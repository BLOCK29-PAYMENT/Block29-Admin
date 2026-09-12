"""
Payment Hub (AsterPOSPaymentHub) operations integration.

Built against the Hub's LIVE API surface (audited 2026-09-11 from the
AsterPOSPaymentHub repo; see PAYMENT_HUB_ADMIN_API_MAP.md). The bundled
"admin-ops-console-kit" endpoints (/api/v1/admin/terminals/*, /admin/errors,
/admin/transactions, JWT bearer auth) were removed from the Hub on 2026-04-12
and are NOT used here.

Live surface used:
  GET  /health                                              (public)
  GET  /ready                                               (X-Admin-Key for per-dependency detail)
  GET  /api/metrics/json, /api/metrics/alerts               (X-Admin-Key)
  GET  /api/v1/admin/merchants                              (X-Admin-Key)
  GET  /api/admin/merchants/{identifier}                    (X-Admin-Key; UUID/hub_mid/int tolerant)
  GET  /api/v1/admin/merchants/{id}/terminals               (X-Admin-Key; static registry rows)
  POST /api/v1/admin/merchants/profiles/{profile_id}/ping   (X-Admin-Key; REAL device probe)
  GET  /api/v1/admin/merchants/{id}/payment-path            (X-Admin-Key; routing config)
  GET  /api/v1/events/stats, /api/v1/events/undelivered     (X-Admin-Key; event delivery)

Architecture: Browser -> Block29 Admin backend -> Payment Hub. The admin key
(PAYMENT_HUB_ADMIN_KEY) lives server-side only and never reaches the browser.

Status semantics (honest by design):
  ONLINE   - positive response received from the Hub
  OFFLINE  - explicit evidence (connection refused)
  DEGRADED - Hub responded with a failure status
  UNKNOWN  - could not determine (timeout, endpoint missing, auth rejected)
  NOT_CONFIGURED - PAYMENT_HUB_URL / PAYMENT_HUB_ADMIN_KEY unset
UNKNOWN is never collapsed into ONLINE or OFFLINE.

Every call sends X-Request-Id for tracing. (The Hub does not yet read inbound
request ids - flagged in the API map as a Hub-side follow-up.)

No financial operations exist here - diagnostics only.
"""
import asyncio
import os
import re
import time
import uuid
from urllib.parse import quote
from typing import Any, Dict, List, Optional

import httpx

# Hub identifiers embedded in URL paths must be plain tokens - anything else
# (/, ?, .., %) could re-point the admin-key request at a different Hub path.
HUB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def valid_hub_id(value: str) -> bool:
    return bool(value and HUB_ID_PATTERN.fullmatch(value))


def _seg(value: str) -> str:
    """Percent-encode a caller-supplied path segment (defense in depth on top
    of endpoint-level validation)."""
    return quote(str(value), safe="")

PAYMENT_HUB_URL = (os.environ.get("PAYMENT_HUB_URL") or "").rstrip("/")
PAYMENT_HUB_ADMIN_KEY = os.environ.get("PAYMENT_HUB_ADMIN_KEY") or ""
PAYMENT_HUB_ENV = os.environ.get("PAYMENT_HUB_ENV", "production")

DEFAULT_TIMEOUT = float(os.environ.get("PAYMENT_HUB_TIMEOUT_SECONDS", "10"))
BULK_PING_MAX = 50
BULK_PING_CONCURRENCY = 5


def hub_configured() -> bool:
    return bool(PAYMENT_HUB_URL and PAYMENT_HUB_ADMIN_KEY)


def new_correlation_id() -> str:
    return f"b29adm-{uuid.uuid4()}"


async def hub_request(
    method: str,
    path: str,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
    correlation_id: Optional[str] = None,
    public: bool = False,
) -> Dict[str, Any]:
    """Call the Hub. Returns a structured result and never raises.

    result: {status: ONLINE|OFFLINE|DEGRADED|UNKNOWN|NOT_CONFIGURED, http_status,
             data, latency_ms, correlation_id, detail}
    """
    correlation_id = correlation_id or new_correlation_id()

    if not PAYMENT_HUB_URL or (not public and not PAYMENT_HUB_ADMIN_KEY):
        return {
            "status": "NOT_CONFIGURED",
            "http_status": None,
            "data": None,
            "latency_ms": None,
            "correlation_id": correlation_id,
            "detail": "Payment Hub is not configured (set PAYMENT_HUB_URL and PAYMENT_HUB_ADMIN_KEY)",
        }

    url = f"{PAYMENT_HUB_URL}{path}"
    headers = {"X-Request-Id": correlation_id}
    if PAYMENT_HUB_ADMIN_KEY:
        headers["X-Admin-Key"] = PAYMENT_HUB_ADMIN_KEY

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, json=json_body, params=params, headers=headers)
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            data = resp.json()
        except Exception:
            data = None
        if resp.status_code == 404:
            return {"status": "UNKNOWN", "http_status": 404, "data": data, "latency_ms": latency_ms,
                    "correlation_id": correlation_id, "detail": f"Hub endpoint not found: {path}"}
        if resp.status_code in (401, 403):
            return {"status": "UNKNOWN", "http_status": resp.status_code, "data": data, "latency_ms": latency_ms,
                    "correlation_id": correlation_id, "detail": "Hub rejected the admin key (check PAYMENT_HUB_ADMIN_KEY / IP allowlist)"}
        if resp.is_success:
            return {"status": "ONLINE", "http_status": resp.status_code, "data": data, "latency_ms": latency_ms,
                    "correlation_id": correlation_id, "detail": None}
        return {"status": "DEGRADED", "http_status": resp.status_code, "data": data, "latency_ms": latency_ms,
                "correlation_id": correlation_id,
                "detail": (data or {}).get("detail") if isinstance(data, dict) else f"HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"status": "UNKNOWN", "http_status": None, "data": None,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "correlation_id": correlation_id, "detail": f"Timeout after {timeout}s"}
    except httpx.ConnectError:
        return {"status": "OFFLINE", "http_status": None, "data": None,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "correlation_id": correlation_id, "detail": "Connection refused - Hub unreachable"}
    except Exception as e:  # pragma: no cover - defensive
        return {"status": "UNKNOWN", "http_status": None, "data": None,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "correlation_id": correlation_id, "detail": f"{type(e).__name__}"}


# ---- live Hub endpoints ----

async def hub_health(correlation_id: Optional[str] = None) -> Dict[str, Any]:
    return await hub_request("GET", "/health", correlation_id=correlation_id, timeout=5, public=True)


async def hub_ready(correlation_id: Optional[str] = None) -> Dict[str, Any]:
    # With a valid X-Admin-Key the Hub returns per-dependency detail
    return await hub_request("GET", "/ready", correlation_id=correlation_id, timeout=8)


async def hub_alerts(correlation_id: Optional[str] = None) -> Dict[str, Any]:
    return await hub_request("GET", "/api/metrics/alerts", correlation_id=correlation_id)


async def hub_metrics_json(correlation_id: Optional[str] = None) -> Dict[str, Any]:
    return await hub_request("GET", "/api/metrics/json", correlation_id=correlation_id)


async def hub_merchants_list() -> Dict[str, Any]:
    return await hub_request("GET", "/api/v1/admin/merchants")


async def hub_merchant_lookup(identifier: str) -> Dict[str, Any]:
    """UUID-tolerant lookup: resolves merchants.user_id (UUID) -> hub_mid -> int id."""
    return await hub_request("GET", f"/api/admin/merchants/{_seg(identifier)}")


async def hub_merchant_terminals(hub_merchant_id: str) -> Dict[str, Any]:
    return await hub_request("GET", f"/api/v1/admin/merchants/{_seg(hub_merchant_id)}/terminals")


async def hub_profile_ping(profile_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """REAL device probe: iPOSpays/Dejavoo SPIn ConnectionStatus or Valor device info."""
    return await hub_request("POST", f"/api/v1/admin/merchants/profiles/{_seg(profile_id)}/ping",
                             correlation_id=correlation_id, timeout=15)


async def hub_payment_path(hub_merchant_id: str) -> Dict[str, Any]:
    return await hub_request("GET", f"/api/v1/admin/merchants/{_seg(hub_merchant_id)}/payment-path")


async def hub_events_stats() -> Dict[str, Any]:
    return await hub_request("GET", "/api/v1/events/stats")


async def hub_events_undelivered(limit: int = 50) -> Dict[str, Any]:
    return await hub_request("GET", "/api/v1/events/undelivered", params={"limit": limit})


def ping_state(result: Dict[str, Any]) -> str:
    """Map a profile-ping hub_request result to online|offline|unknown, honestly."""
    if result["status"] == "ONLINE" and isinstance(result.get("data"), dict):
        conn = str(result["data"].get("connectivity_status", "")).lower()
        if conn == "online":
            return "online"
        if conn == "offline":
            return "offline"
        return "unknown"  # timeout/unknown from the Hub stays unknown
    if result["status"] == "OFFLINE":
        return "unknown"  # the HUB was unreachable - proves nothing about the terminal
    return "unknown"


async def bulk_profile_ping(profile_ids: List[str], correlation_id: str) -> Dict[str, Any]:
    """Ping up to BULK_PING_MAX processor profiles with bounded concurrency."""
    ids = profile_ids[:BULK_PING_MAX]
    sem = asyncio.Semaphore(BULK_PING_CONCURRENCY)

    async def one(pid: str):
        async with sem:
            result = await hub_profile_ping(pid, correlation_id=f"{correlation_id[:40]}-{pid[:8]}")
            return pid, result

    pairs = await asyncio.gather(*(one(p) for p in ids))
    results = []
    counts = {"online": 0, "offline": 0, "unknown": 0}
    for pid, res in pairs:
        state = ping_state(res)
        counts[state] += 1
        results.append({
            "profile_id": pid,
            "state": state,
            "latency_ms": res["latency_ms"],
            "correlation_id": res["correlation_id"],
            "detail": res["detail"] or (res.get("data") or {}).get("connectivity_status") if isinstance(res.get("data"), dict) else res["detail"],
        })
    return {"results": results, "counts": counts, "requested": len(profile_ids), "pinged": len(ids)}
