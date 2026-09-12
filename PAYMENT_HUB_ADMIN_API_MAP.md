# Payment Hub ↔ Admin API Map

Source of truth: full read of the `BLOCK29-PAYMENT/AsterPOSPaymentHub` repo (HEAD `93676fd`, 2026-09-11).
The Hub is FastAPI ("123Cents Payment Hub" v2.1.0), deployed at `https://www.123cents.com`, port 8001.

## ⚠️ Critical discovery

The Hub ships two Next.js console kits (`admin-ops-console-kit/`, `gateway-admin-integration/`)
whose endpoints (`/api/v1/admin/terminals/*`, `/admin/errors`, `/admin/transactions`,
`/admin/processors/*`, JWT Bearer admin auth) were **removed from the mounted app on
2026-04-12** (`backend/api/v1/router.py` lines 3–14). 11 of the kit's 12 proxy routes point at
dead endpoints, and **no live Hub endpoint accepts an admin JWT**. This integration therefore
targets the LIVE surface below, authenticated with **`X-Admin-Key`** (Hub env `ADMIN_API_KEY`,
optionally IP-allowlisted via `ADMIN_API_KEY_IP_ALLOWLIST`).

## Admin function → Hub endpoint map

| Admin function | Hub endpoint | Available? | Auth | Safe? | Action taken |
|---|---|---|---|---|---|
| Hub health | `GET /health` | YES | none | yes | Used by `/api/hub/status` |
| Hub readiness + dependency detail | `GET /ready` | YES | `X-Admin-Key` for detail | yes | Used by `/api/hub/status` |
| Hub alerts / error-rate monitoring | `GET /api/metrics/alerts`, `GET /api/metrics/json` | YES | `X-Admin-Key` | yes | Used by `/api/hub/status` |
| Merchant lookup (UUID/hub_mid/id tolerant) | `GET /api/admin/merchants/{identifier}` | YES | `X-Admin-Key` | yes | Used by hub-view, link verification, readiness |
| Merchant list | `GET /api/v1/admin/merchants` | YES | `X-Admin-Key` | yes | Available in client (`hub_merchants_list`) |
| Merchant terminals (registry rows) | `GET /api/v1/admin/merchants/{id}/terminals` | YES | `X-Admin-Key` | yes | Used by hub-view |
| **Terminal ping (real device probe)** | `POST /api/v1/admin/merchants/profiles/{profile_id}/ping` | YES — SPIn `ConnectionStatus` for iPOSpays/Dejavoo, Valor device info for Valor | `X-Admin-Key` | yes, non-financial | Used by ping, bulk-ping, readiness |
| Terminal live status (merchant-scoped) | `GET /api/hub/v1/merchant/terminals/status` | YES but requires a **merchant `X-Api-Key`**, not the admin key | `X-Api-Key` | yes | NOT used (admin holds no merchant keys); profile ping covers the need |
| Routing / payment path | `GET /api/v1/admin/merchants/{id}/payment-path`, `/payment-channels` | YES | `X-Admin-Key` | yes | payment-path used by hub-view + readiness |
| Recent events | `GET /api/v1/events/stats`, `GET /api/v1/events/undelivered` | YES | `X-Admin-Key` | yes | Used by `/api/hub/events` |
| Deep diagnostics (snapshot, outbox, webhooks) | `/api/debug/*` | YES but off by default (`DEBUG_API_ENABLED` + separate Bearer `DEBUG_API_TOKEN`) | Bearer | yes | Not wired; candidate follow-up |
| Bulk terminal ping | — | **MISSING in Hub** | — | — | Implemented admin-side as a bounded fan-out (concurrency 5, max 50) over the single ping; a native Hub `POST /ops/terminals/bulk-ping` remains the better long-term home |
| Terminal readiness | — | **MISSING in Hub** | — | — | Computed admin-side from real records + live Hub responses (`/api/hub/merchants/{id}/readiness`) |
| Correlation-ID propagation | — | **MISSING in Hub** (no request-id middleware; it only *emits* `X-Correlation-Id` on outbound webhooks) | — | — | Admin sends `X-Request-Id` on every call and records its correlation IDs in audit logs; adding inbound request-id middleware is a Hub-side follow-up |
| Transactions/errors feeds from the old kit | `/api/v1/admin/transactions*`, `/admin/errors*` | **REMOVED from Hub 2026-04-12** | — | — | Not used; events + metrics/alerts serve monitoring instead |

## Hub identity model (for mappings)

Hub `merchants`: `id` (int, canonical), `hub_mid` (Hub-issued MID), `user_id` (external UUID),
`api_key` (merchant key). `GET /api/admin/merchants/{identifier}` resolves any of the three.
Admin's `hub_merchant_links.hub_merchant_id` stores whichever identifier ops uses; saving a link
verifies it against the live Hub (404 ⇒ rejected).

Hub terminal-ish units: `terminals` (serial/EPI/TPN registry rows) and
`merchant_processor_profiles` (the credential/routing SSOT — **the pingable unit**). The admin
console pings profiles; per-profile cached `connectivity_status` also comes back on merchant lookup.

## Admin-side configuration

| Env var (admin backend) | Purpose |
|---|---|
| `PAYMENT_HUB_URL` | Hub base URL (e.g. `https://www.123cents.com`) |
| `PAYMENT_HUB_ADMIN_KEY` | Hub `ADMIN_API_KEY` value; sent as `X-Admin-Key`, server-side only, never to the browser |
| `PAYMENT_HUB_ENV` | Label shown in UI (`production` / `staging` / ...) — display only |
| `PAYMENT_HUB_TIMEOUT_SECONDS` | Per-call timeout (default 10; ping 15, health 5) |

Timeout ⇒ status UNKNOWN (never OFFLINE). Connection refused ⇒ Hub OFFLINE (terminal state stays
UNKNOWN — an unreachable Hub proves nothing about a device). 401/403 ⇒ UNKNOWN with an actionable
detail. Not configured ⇒ NOT_CONFIGURED, shown prominently, never as healthy.

## Hub-side follow-ups discovered during the audit (need Hub repo changes — read-only access here)

1. **`ecs-task-definition.json` at the Hub repo root contains plaintext production credentials committed to git** (DB connection string with password, webhook HMAC secret, encryption key). Rotate and move to secret storage. **URGENT.**
2. `X-Internal-Secret` guard accepts ANY non-empty header when `ADMIN_TO_HUB_SHARED_SECRET` is unset (`valor_crm.py:57`).
3. `GET /api/hub/v1/billing/debug/snapshot` has no auth dependency at all.
4. Test-console endpoints `GET/POST /api/admin/test-console/terminals*` query a `hub_terminal` table that has no migration or model — they 500.
5. `.sql` files under `backend/migrations/versions/` are never applied by Alembic (test-console login breaks on clean deploys).
6. No inbound request-id middleware (correlation gap above).
7. Optional: native `POST /ops/terminals/bulk-ping` and readiness endpoints per the ops spec.
