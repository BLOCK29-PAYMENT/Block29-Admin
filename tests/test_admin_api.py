"""
Block29 Admin API tests.

Runs the real FastAPI app with the database helper layer monkeypatched, so
auth, RBAC, validation, rate limiting, and endpoint wiring are tested without
a live MySQL instance. backend_test.py remains the live integration smoke test.
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_DATABASE", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import server  # noqa: E402

client = TestClient(server.app)

ADMIN_HASH = server.hash_password("correct-password")


class FakeDB:
    """Configurable stand-in for the raw-SQL helper layer."""

    def __init__(self):
        self.users = {}
        self.one_results = []   # queued fetch_one results (FIFO); fallback None
        self.all_results = []   # queued fetch_all results (FIFO); fallback []
        self.inserts = []
        self.updates = []
        self.deletes = []
        # Row returned for the per-request token-holder activation check
        # (get_current_user); None simulates a deleted account.
        self.current_user_row = {"is_active": 1}

    async def fetch_one(self, query, params=None):
        q = " ".join(query.split()).lower()
        if "from users where email" in q:
            return self.users.get((params or {}).get("email"))
        if "select is_active from users where id" in q:
            return self.current_user_row
        if self.one_results:
            return self.one_results.pop(0)
        return None

    async def fetch_all(self, query, params=None):
        if self.all_results:
            return self.all_results.pop(0)
        return []

    async def insert_row(self, table, data):
        self.inserts.append((table, data))

    async def update_row(self, table, data, where, params):
        self.updates.append((table, data))

    async def delete_row(self, table, where, params):
        self.deletes.append((table, params))


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(server, "fetch_one", fake.fetch_one)
    monkeypatch.setattr(server, "fetch_all", fake.fetch_all)
    monkeypatch.setattr(server, "insert_row", fake.insert_row)
    monkeypatch.setattr(server, "update_row", fake.update_row)
    monkeypatch.setattr(server, "delete_row", fake.delete_row)
    server._login_failures.clear()
    return fake


def token_for(role, user_id="u1", email="user@block29.com"):
    return server.create_token(user_id, email, role)


def auth(role="SUPER_ADMIN", **kw):
    return {"Authorization": f"Bearer {token_for(role, **kw)}"}


def make_user(email="admin@block29.com", active=1, role="SUPER_ADMIN"):
    return {
        "id": "u1", "email": email, "password": ADMIN_HASH,
        "name": "Admin", "role": role, "is_active": active,
        "created_at": "2026-01-01 00:00:00",
    }


# ---------------- security: register ----------------

def test_register_unauthenticated_rejected(db):
    r = client.post("/api/auth/register", json={
        "email": "attacker@example.com", "password": "longenough1", "name": "x", "role": "SUPER_ADMIN"})
    assert r.status_code == 403


def test_register_non_super_admin_rejected(db):
    r = client.post("/api/auth/register", headers=auth("OPERATIONS"), json={
        "email": "x@example.com", "password": "longenough1", "name": "x", "role": "READ_ONLY"})
    assert r.status_code == 403


def test_register_weak_password_rejected(db):
    r = client.post("/api/auth/register", headers=auth(), json={
        "email": "x@example.com", "password": "short", "name": "x", "role": "READ_ONLY"})
    assert r.status_code == 422


def test_register_invalid_role_rejected(db):
    r = client.post("/api/auth/register", headers=auth(), json={
        "email": "x@example.com", "password": "longenough1", "name": "x", "role": "RISK"})
    assert r.status_code == 400


def test_register_ok_and_audited(db):
    r = client.post("/api/auth/register", headers=auth(), json={
        "email": "new@block29.com", "password": "longenough1", "name": "New User", "role": "READ_ONLY"})
    assert r.status_code == 200
    tables = [t for t, _ in db.inserts]
    assert "users" in tables and "audit_logs" in tables


# ---------------- security: login ----------------

def test_login_wrong_password(db):
    db.users["admin@block29.com"] = make_user()
    r = client.post("/api/auth/login", json={"email": "admin@block29.com", "password": "wrong"})
    assert r.status_code == 401
    assert any(d.get("action") == "LOGIN_FAILED" for t, d in db.inserts if t == "audit_logs")


def test_login_rate_limited_after_failures(db):
    db.users["admin@block29.com"] = make_user()
    for _ in range(server.LOGIN_MAX_FAILURES):
        client.post("/api/auth/login", json={"email": "admin@block29.com", "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": "admin@block29.com", "password": "correct-password"})
    assert r.status_code == 429


def test_login_inactive_user_blocked(db):
    db.users["admin@block29.com"] = make_user(active=0)
    r = client.post("/api/auth/login", json={"email": "admin@block29.com", "password": "correct-password"})
    assert r.status_code == 403


def test_login_success_returns_token_and_audits(db):
    db.users["admin@block29.com"] = make_user()
    r = client.post("/api/auth/login", json={"email": "admin@block29.com", "password": "correct-password"})
    assert r.status_code == 200
    payload = pyjwt.decode(r.json()["token"], os.environ["JWT_SECRET"], algorithms=["HS256"])
    assert payload["role"] == "SUPER_ADMIN"
    assert any(d.get("action") == "LOGIN" for t, d in db.inserts if t == "audit_logs")


# ---------------- security: tokens ----------------

def test_forged_jwt_rejected(db):
    forged = pyjwt.encode({"user_id": "u1", "email": "a@b.c", "role": "SUPER_ADMIN",
                           "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                          "wrong-secret", algorithm="HS256")
    r = client.get("/api/users", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_expired_jwt_rejected(db):
    expired = pyjwt.encode({"user_id": "u1", "email": "a@b.c", "role": "SUPER_ADMIN",
                            "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
                           os.environ["JWT_SECRET"], algorithm="HS256")
    r = client.get("/api/users", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


# ---------------- RBAC ----------------

def test_users_list_requires_super_admin(db):
    assert client.get("/api/users", headers=auth("OPERATIONS")).status_code == 403
    assert client.get("/api/users", headers=auth("READ_ONLY")).status_code == 403


def test_transactions_forbidden_for_read_only(db):
    assert client.get("/api/transactions", headers=auth("READ_ONLY")).status_code == 403


def test_logs_require_super_admin(db):
    assert client.get("/api/logs", headers=auth("OPERATIONS")).status_code == 403


def test_merchant_create_forbidden_for_support(db):
    r = client.post("/api/merchants", headers=auth("SUPPORT"), json={"business_name": "X"})
    assert r.status_code == 403


def test_risk_role_removed():
    assert "RISK" not in server.VALID_ROLES


def test_role_update_rejects_unknown_role(db):
    r = client.put("/api/users/u2/role?role=RISK", headers=auth())
    assert r.status_code == 400


def test_cannot_deactivate_self(db):
    r = client.put("/api/users/u1/status", headers=auth(), json={"is_active": False})
    assert r.status_code == 400


# ---------------- removed fake features stay removed ----------------

@pytest.mark.parametrize("method,path", [
    ("post", "/api/virtual-terminal/process"),
    ("post", "/api/virtual-terminal/refund/abc"),
    ("get", "/api/block29/provisions"),
    ("post", "/api/block29/provision-terminal"),
    ("get", "/api/agents"),
    ("get", "/api/agents/merchants"),
    ("get", "/api/reports/settlement"),
    ("post", "/api/admin/terminals/abc/pair"),
    ("post", "/api/transactions"),
])
def test_removed_endpoints_are_gone(db, method, path):
    r = getattr(client, method)(path, headers=auth())
    assert r.status_code in (404, 405), f"{path} still reachable: {r.status_code}"


# ---------------- merchants ----------------

def test_merchant_duplicate_name_rejected(db):
    db.one_results = [{"id": "existing"}]  # duplicate lookup
    r = client.post("/api/merchants", headers=auth(), json={"business_name": "Dup Cafe"})
    assert r.status_code == 400


def test_merchant_create_ok_and_audited(db):
    db.one_results = [None]  # no duplicate
    r = client.post("/api/merchants", headers=auth(), json={"business_name": "New Cafe"})
    assert r.status_code == 200
    tables = [t for t, _ in db.inserts]
    assert "merchants" in tables and "audit_logs" in tables


def test_merchant_delete_blocked_with_dependencies(db):
    db.one_results = [{"count": 2}, {"count": 5}]  # terminals, transactions
    r = client.delete("/api/merchants/m1", headers=auth())
    assert r.status_code == 400
    assert db.deletes == []


def test_merchant_delete_ok_without_dependencies(db):
    db.one_results = [{"count": 0}, {"count": 0}]
    r = client.delete("/api/merchants/m1", headers=auth())
    assert r.status_code == 200
    # merchant row + its hub mapping (prevents orphaned unique-key rows)
    assert len(db.deletes) == 2


# ---------------- pagination envelopes ----------------

def test_merchants_paginated_envelope(db):
    db.one_results = [{"total": 0}]
    r = client.get("/api/merchants", headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}


def test_transactions_envelope_includes_summary(db):
    db.one_results = [{"total": 0}, {"count": 0, "volume": 0, "approved": 0}]
    r = client.get("/api/transactions", headers=auth())
    assert r.status_code == 200
    assert "summary" in r.json()


def test_page_size_clamped(db):
    db.one_results = [{"total": 0}]
    r = client.get("/api/merchants?page_size=99999", headers=auth())
    assert r.json()["page_size"] <= 500


# ---------------- VAR sheet field coverage ----------------

UI_VAR_FIELDS = [
    "merchant_name", "merchant_number", "terminal_status", "v_number_primary",
    "v_number_secondary", "industry_type", "visa_mcc", "terminal_number", "bin",
    "agent", "chain", "store_number", "location_number", "edc_primary",
    "edc_secondary", "street_address", "city", "state", "postal_code", "phone",
    "country", "currency_code", "time_zone", "time_zone_differential",
    "card_types", "networks", "host_capture_participant", "amex_se", "disc_se",
    "aba", "reimbursement_att", "raw_comments",
]

def test_varsheet_model_covers_every_ui_field():
    """Every field the VAR review form can edit must be accepted by the save model,
    otherwise edits are silently dropped (the original data-loss bug)."""
    model_fields = set(server.VarSheetParsedData.model_fields.keys())
    missing = [f for f in UI_VAR_FIELDS if f not in model_fields]
    assert missing == [], f"UI fields silently dropped on save: {missing}"


# ---------------- security headers / misc ----------------

def test_security_headers_present():
    r = client.get("/api/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_root_is_rebranded():
    body = client.get("/api/").json()
    assert "Block29" in body["message"]
    assert "salonbookin" not in str(body).lower()


def test_no_random_approval_code_in_backend():
    src = open(os.path.join(os.path.dirname(__file__), "..", "backend", "server.py")).read()
    assert "import random" not in src
    assert "random.random" not in src


# ---------------- Payment Hub integration ----------------

import hub as hub_module


def hub_result(status="ONLINE", data=None, http_status=200, detail=None, latency=42):
    return {"status": status, "http_status": http_status, "data": data,
            "latency_ms": latency, "correlation_id": "b29adm-test", "detail": detail}


def test_hub_not_configured_is_honest(db):
    """Without PAYMENT_HUB_URL/KEY every check reports NOT_CONFIGURED - never healthy."""
    assert not hub_module.hub_configured()
    r = client.get("/api/hub/status", headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is False
    assert body["overall"] == "NOT_CONFIGURED"
    assert all(c["status"] == "NOT_CONFIGURED" for c in body["checks"])


def test_hub_ping_requires_diagnostic_role(db):
    r = client.post("/api/hub/profiles/abc/ping", headers=auth("READ_ONLY"))
    assert r.status_code == 403


def test_hub_bulk_ping_requires_operations(db):
    r = client.post("/api/hub/profiles/bulk-ping", headers=auth("SUPPORT"),
                    json={"profile_ids": ["a"]})
    assert r.status_code == 403


def test_hub_bulk_ping_bounded(db):
    r = client.post("/api/hub/profiles/bulk-ping", headers=auth(),
                    json={"profile_ids": [f"p{i}" for i in range(51)]})
    assert r.status_code == 422  # max 50 enforced by the request model


def test_hub_bulk_ping_unconfigured_503(db):
    r = client.post("/api/hub/profiles/bulk-ping", headers=auth(), json={"profile_ids": ["a"]})
    assert r.status_code == 503


def test_hub_ping_audited(db, monkeypatch):
    async def fake_ping(pid, correlation_id=None):
        return hub_result(data={"connectivity_status": "online"})
    monkeypatch.setattr(hub_module, "hub_profile_ping", fake_ping)
    r = client.post("/api/hub/profiles/prof-1/ping", headers=auth())
    assert r.status_code == 200
    assert r.json()["state"] == "online"
    assert any(d.get("action") == "TERMINAL_PING" for t, d in db.inserts if t == "audit_logs")


def test_ping_state_never_invents_results():
    # Hub itself unreachable proves nothing about the terminal -> unknown
    assert hub_module.ping_state(hub_result(status="OFFLINE", http_status=None)) == "unknown"
    # Hub says offline -> offline
    assert hub_module.ping_state(hub_result(data={"connectivity_status": "offline"})) == "offline"
    # Hub says timeout/unknown -> unknown, not offline, not online
    assert hub_module.ping_state(hub_result(data={"connectivity_status": "timeout"})) == "unknown"
    assert hub_module.ping_state(hub_result(status="UNKNOWN", http_status=None)) == "unknown"


def test_hub_link_rejects_unknown_hub_merchant(db, monkeypatch):
    async def fake_lookup(identifier):
        return hub_result(status="UNKNOWN", http_status=404, detail="Hub endpoint not found")
    monkeypatch.setattr(hub_module, "hub_merchant_lookup", fake_lookup)
    db.one_results = [{"id": "m1"}]  # merchant exists
    r = client.put("/api/hub/links/merchants/m1", headers=auth(), json={"hub_merchant_id": "nope"})
    assert r.status_code == 400


def test_hub_link_verified_and_audited(db, monkeypatch):
    async def fake_lookup(identifier):
        return hub_result(data={"id": 7, "hub_mid": "HMID001"})
    monkeypatch.setattr(hub_module, "hub_merchant_lookup", fake_lookup)
    db.one_results = [{"id": "m1"}, None]  # merchant exists; no existing link
    r = client.put("/api/hub/links/merchants/m1", headers=auth(), json={"hub_merchant_id": "HMID001"})
    assert r.status_code == 200
    assert r.json()["verified_against_hub"] is True
    assert any(d.get("action") == "MERCHANT_HUB_LINK" for t, d in db.inserts if t == "audit_logs")


def test_readiness_unknown_hub_blocks_ready(db, monkeypatch):
    async def fake_health(cid=None):
        return hub_result(status="UNKNOWN", http_status=None, detail="Timeout after 5s")
    monkeypatch.setattr(hub_module, "hub_health", fake_health)
    # fetch_one sequence: merchant, var count, hub link
    db.one_results = [
        {"id": "m1", "status": "active"},
        {"count": 1},
        {"hub_merchant_id": "HMID001"},
    ]
    # fetch_all: terminals list
    db.all_results = [[{"id": "t1", "terminal_number": "0001"}]]
    r = client.get("/api/hub/merchants/m1/readiness", headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["overall"] == "NOT_READY"  # unknown critical check must block READY
    hub_check = next(c for c in body["checks"] if c["check"] == "Hub reachable")
    assert hub_check["status"] == "UNKNOWN"


def test_hub_secrets_never_reach_browser_payloads():
    """The hub client must not echo the admin key into responses."""
    import inspect
    src = inspect.getsource(hub_module)
    assert "PAYMENT_HUB_ADMIN_KEY" in src
    # the key is only used for the outbound header, never returned
    assert 'data["admin_key"]' not in src and "return PAYMENT_HUB_ADMIN_KEY" not in src


# ---------------- code-review regression fixes ----------------

def test_deactivated_user_token_revoked_immediately(db):
    """Deactivation must cut off existing tokens, not wait for expiry."""
    db.current_user_row = {"is_active": 0}
    r = client.get("/api/merchants", headers=auth())
    assert r.status_code == 403


def test_deleted_user_token_rejected(db):
    db.current_user_row = None
    r = client.get("/api/merchants", headers=auth())
    assert r.status_code == 401


def test_xff_spoofing_cannot_bypass_login_rate_limit(db):
    """TRUSTED_PROXY_HOPS defaults to 0: X-Forwarded-For is ignored, so a
    brute-forcer rotating XFF values still hits the same rate-limit key."""
    db.users["admin@block29.com"] = make_user()
    for i in range(server.LOGIN_MAX_FAILURES):
        client.post("/api/auth/login",
                    json={"email": "admin@block29.com", "password": "wrong"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"})
    r = client.post("/api/auth/login",
                    json={"email": "admin@block29.com", "password": "correct-password"},
                    headers={"X-Forwarded-For": "10.9.9.9"})
    assert r.status_code == 429


def test_cannot_change_own_role(db):
    r = client.put("/api/users/u1/role?role=READ_ONLY", headers=auth())
    assert r.status_code == 400


def test_role_change_unknown_user_404(db):
    db.one_results = [None]  # target lookup
    r = client.put("/api/users/u2/role?role=READ_ONLY", headers=auth())
    assert r.status_code == 404


def test_login_failure_tracker_bounded():
    server._login_failures.clear()
    server._login_failures.update({f"stale|{i}": [0.0] for i in range(6000)})
    server.record_login_failure("new@block29.com")
    assert len(server._login_failures) < 6000  # stale keys pruned
    server._login_failures.clear()


# ---------------- security-review fix: Hub identifier injection ----------------

def test_hub_link_rejects_path_traversal_identifier(db):
    db.one_results = [{"id": "m1"}]
    r = client.put("/api/hub/links/merchants/m1", headers=auth(),
                   json={"hub_merchant_id": "../../api/metrics/json"})
    assert r.status_code == 422  # pydantic pattern rejects non-token identifiers


def test_hub_link_rejects_query_injection_identifier(db):
    db.one_results = [{"id": "m1"}]
    r = client.put("/api/hub/links/merchants/m1", headers=auth(),
                   json={"hub_merchant_id": "x?limit=99"})
    assert r.status_code == 422


def test_hub_ping_rejects_malformed_profile_id(db):
    r = client.post("/api/hub/profiles/..%3Fx/ping", headers=auth())
    assert r.status_code == 400


def test_hub_bulk_ping_rejects_malformed_ids(db, monkeypatch):
    monkeypatch.setattr(hub_module, "PAYMENT_HUB_URL", "http://hub.test")
    monkeypatch.setattr(hub_module, "PAYMENT_HUB_ADMIN_KEY", "k")
    r = client.post("/api/hub/profiles/bulk-ping", headers=auth(),
                    json={"profile_ids": ["good-id", "../escape"]})
    assert r.status_code == 400


def test_hub_path_segments_are_encoded():
    assert hub_module._seg("../x") == "..%2Fx"
    assert hub_module._seg("a?b=c") == "a%3Fb%3Dc"
    assert hub_module.valid_hub_id("HMID-001_x")
    assert not hub_module.valid_hub_id("../../etc")
    assert not hub_module.valid_hub_id("a?b")
    assert not hub_module.valid_hub_id("")
