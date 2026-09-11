# Admin Endpoint Audit

41 routes under `/api` (verified by importing the app and enumerating routes).
"Used by UI" names the page. All mutating endpoints are audit logged. Tests = covered by
`tests/test_admin_api.py` (unit/RBAC) and/or `backend_test.py` (live smoke).

| Method | Path | Used by UI | Auth | Role | Mutates | Audit | Tested | Verdict |
|---|---|---|---|---|---|---|---|---|
| GET | /api/ | — (version probe) | none | — | no | — | ✅ | KEEP |
| GET | /api/health | deploy health check | none | — | no | — | ✅ | KEEP |
| POST | /api/auth/login | Login | none | — | no (audit rows) | LOGIN/LOGIN_FAILED | ✅ | KEEP |
| POST | /api/auth/register | Users (Add User) | JWT | SUPER_ADMIN | yes | CREATE | ✅ | KEEP |
| GET | /api/auth/me | session bootstrap | JWT | any | no | — | ✅ | KEEP |
| GET | /api/users | Users | JWT | SUPER_ADMIN | no | — | ✅ | KEEP |
| PUT | /api/users/{id}/role | Users | JWT | SUPER_ADMIN | yes | UPDATE | ✅ | KEEP |
| PUT | /api/users/{id}/status | Users | JWT | SUPER_ADMIN | yes | UPDATE | ✅ | KEEP |
| GET | /api/merchants | Merchants + 4 dropdowns | JWT | any | no | — | ✅ | KEEP |
| GET | /api/merchants/{id} | (detail fetch after update) | JWT | any | no | — | via update | KEEP |
| POST | /api/merchants | Merchants | JWT | SA/OPS | yes | CREATE | ✅ | KEEP |
| PUT | /api/merchants/{id} | Merchants | JWT | SA/OPS | yes | UPDATE | live | KEEP |
| DELETE | /api/merchants/{id} | Merchants | JWT | SUPER_ADMIN | yes (guarded) | DELETE | ✅ | KEEP |
| POST | /api/admin/varsheet/upload | VAR Sheet | JWT | SA/OPS | yes | UPLOAD | live | KEEP |
| POST | /api/admin/varsheet/{id}/parse | VAR Sheet | JWT | SA/OPS | yes | PARSE | live | KEEP |
| GET | /api/admin/varsheet/{id} | VAR Sheet | JWT | any | no | — | live | KEEP |
| GET | /api/admin/varsheets | VAR Sheet | JWT | any | no | — | live | KEEP |
| PUT | /api/admin/varsheet/{id} | VAR Sheet (Save Draft) | JWT | SA/OPS | yes | UPDATE | model test | KEEP |
| POST | /api/admin/terminals | Terminals + VAR page | JWT | SA/OPS | yes | CREATE | live | KEEP |
| GET | /api/admin/terminals | Terminals + Hub page | JWT | any | no | — | ✅ | KEEP |
| GET | /api/admin/terminals/{id} | (after update) | JWT | any | no | — | via update | KEEP |
| PUT | /api/admin/terminals/{id} | (API; UI edit is future) | JWT | SA/OPS | yes | UPDATE | — | KEEP |
| POST | /api/admin/terminals/{id}/provision | Terminals ("Record Provisioning") | JWT | SA/OPS | yes | PROVISION | live | KEEP |
| POST | /api/admin/terminals/{id}/mark-live | Terminals ("Confirm Live") | JWT | SA/OPS | yes | MARK_LIVE | live | KEEP |
| GET | /api/transactions | Transactions | JWT | SA/OPS/SUPPORT | no | — | ✅ | KEEP |
| GET | /api/reports/transactions | Reports | JWT | SA/OPS/SUPPORT | no | — | live | KEEP |
| GET | /api/reports/batches | Reports | JWT | SA/OPS/SUPPORT | no | — | live | KEEP |
| GET | /api/reports/export | Reports + Transactions export | JWT | SA/OPS/SUPPORT | no (audited) | EXPORT | live | KEEP |
| GET | /api/logs | System Logs | JWT | SUPER_ADMIN | no | — | ✅ | KEEP |
| GET | /api/logs/actions | System Logs filters | JWT | SUPER_ADMIN | no | — | live | KEEP |
| GET | /api/logs/export | System Logs export | JWT | SUPER_ADMIN | no (audited) | EXPORT | live | KEEP |
| GET | /api/dashboard/stats | Dashboard | JWT | any | no | — | live | KEEP |
| GET | /api/hub/status | Hub page + Dashboard card | JWT | any | no (manual runs audited) | HUB_HEALTH_CHECK | ✅ | KEEP |
| GET | /api/hub/merchants/{id}/hub-view | Hub page (Merchant Terminals) | JWT | any | no | — | — | KEEP |
| GET | /api/hub/merchants/{id}/readiness | Hub page (Readiness) | JWT | SA/OPS/SUPPORT | no (audited) | READINESS_CHECK | ✅ | KEEP |
| POST | /api/hub/profiles/{id}/ping | Hub page | JWT | SA/OPS/SUPPORT | no (audited) | TERMINAL_PING | ✅ | KEEP |
| POST | /api/hub/profiles/bulk-ping | Hub page | JWT | SA/OPS | no (audited) | TERMINAL_BULK_PING | ✅ | KEEP |
| GET | /api/hub/events | Hub page (Events) | JWT | SA/OPS/SUPPORT | no | — | — | KEEP |
| GET | /api/hub/links | Hub page (Mappings) | JWT | any | no | — | — | KEEP |
| PUT | /api/hub/links/merchants/{id} | Hub page (Verify & Save) | JWT | SA/OPS | yes | MERCHANT_HUB_LINK | ✅ | KEEP |
| PUT | /api/hub/links/terminals/{id} | API-only for now (UI follow-up) | JWT | SA/OPS | yes | TERMINAL_HUB_LINK | — | KEEP (documented) |

Removed legacy endpoints (verified 404 by tests): `/virtual-terminal/*`, `/block29/*`,
`/agents*`, `/reports/settlement`, `/admin/terminals/{id}/pair`, `POST /transactions`.
No unreachable endpoints remain.
