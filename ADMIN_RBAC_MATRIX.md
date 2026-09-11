# Admin RBAC Matrix

Roles: `SUPER_ADMIN` · `OPERATIONS` · `SUPPORT` · `READ_ONLY`.
(`RISK` was removed — it was never checked by any endpoint. There is no separate `ADMIN` role;
`OPERATIONS` fills the "view + safe diagnostics + boarding" tier.)

Legend: ✅ allowed · ❌ 403 · "any" = any authenticated user (all four roles).
Every mutating ✅ writes an audit row (action name in the last column).

| Endpoint / Action | SUPER_ADMIN | OPERATIONS | SUPPORT | READ_ONLY | Audit action |
|---|---|---|---|---|---|
| POST /auth/login | public | public | public | public | LOGIN / LOGIN_FAILED |
| GET /auth/me | ✅ | ✅ | ✅ | ✅ | — |
| POST /auth/register (create user) | ✅ | ❌ | ❌ | ❌ | CREATE user |
| GET /users | ✅ | ❌ | ❌ | ❌ | — |
| PUT /users/{id}/role | ✅ | ❌ | ❌ | ❌ | UPDATE user |
| PUT /users/{id}/status (de/activate) | ✅ | ❌ | ❌ | ❌ | UPDATE user |
| GET /merchants, /merchants/{id} | any | any | any | any | — |
| POST /merchants | ✅ | ✅ | ❌ | ❌ | CREATE merchant |
| PUT /merchants/{id} | ✅ | ✅ | ❌ | ❌ | UPDATE merchant |
| DELETE /merchants/{id} (dependency-guarded) | ✅ | ❌ | ❌ | ❌ | DELETE merchant |
| GET /admin/varsheets, /admin/varsheet/{id} | any | any | any | any | — |
| POST /admin/varsheet/upload | ✅ | ✅ | ❌ | ❌ | UPLOAD varsheet |
| POST /admin/varsheet/{id}/parse | ✅ | ✅ | ❌ | ❌ | PARSE varsheet |
| PUT /admin/varsheet/{id} | ✅ | ✅ | ❌ | ❌ | UPDATE varsheet |
| GET /admin/terminals, /{id} | any | any | any | any | — |
| POST /admin/terminals | ✅ | ✅ | ❌ | ❌ | CREATE terminal |
| PUT /admin/terminals/{id} | ✅ | ✅ | ❌ | ❌ | UPDATE terminal |
| POST /admin/terminals/{id}/provision | ✅ | ✅ | ❌ | ❌ | PROVISION terminal |
| POST /admin/terminals/{id}/mark-live | ✅ | ✅ | ❌ | ❌ | MARK_LIVE terminal |
| GET /transactions | ✅ | ✅ | ✅ | ❌ | — |
| GET /reports/transactions, /batches | ✅ | ✅ | ✅ | ❌ | — |
| GET /reports/export (CSV) | ✅ | ✅ | ✅ | ❌ | EXPORT report |
| GET /logs, /logs/actions | ✅ | ❌ | ❌ | ❌ | — |
| GET /logs/export | ✅ | ❌ | ❌ | ❌ | EXPORT report |
| GET /dashboard/stats | any | any | any | any | — |
| **Payment Hub** | | | | | |
| GET /hub/status (view health) | any | any | any | any | HUB_HEALTH_CHECK (manual runs) |
| GET /hub/merchants/{id}/hub-view | any | any | any | any | — |
| GET /hub/links | any | any | any | any | — |
| GET /hub/events | ✅ | ✅ | ✅ | ❌ | — |
| POST /hub/profiles/{id}/ping (safe diagnostic) | ✅ | ✅ | ✅ | ❌ | TERMINAL_PING |
| POST /hub/profiles/bulk-ping | ✅ | ✅ | ❌ | ❌ | TERMINAL_BULK_PING |
| GET /hub/merchants/{id}/readiness | ✅ | ✅ | ✅ | ❌ | READINESS_CHECK |
| PUT /hub/links/merchants/{id} | ✅ | ✅ | ❌ | ❌ | MERCHANT_HUB_LINK |
| PUT /hub/links/terminals/{id} | ✅ | ✅ | ❌ | ❌ | TERMINAL_HUB_LINK |
| Future processor-modifying Hub operations | ✅ only | ❌ | ❌ | ❌ | (separate approved workflows — none exist today) |

Enforcement: every row above maps 1:1 to a `Depends(require_roles(...))` or
`Depends(get_current_user)` in `backend/server.py`; the RBAC tests in
`tests/test_admin_api.py` assert the deny cases.
