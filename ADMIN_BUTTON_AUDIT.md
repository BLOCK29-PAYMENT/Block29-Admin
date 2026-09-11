# Admin Button / Control Audit

Every visible interactive control, traced source-to-handler-to-endpoint. "Verified" =
handler exists, endpoint exists and is mounted, success path proven by unit test, live test,
or direct code trace this pass. Zero dead controls remain (the dead ones found in the audit —
Transactions Export, VAR Mark Live, notification bell, header Settings item, Forgot Password,
Remember Me, app-store badges — were removed or wired in earlier commits and are guarded by
smoke tests).

| Page | Control | Handler | Endpoint | Expected result | Verified |
|---|---|---|---|---|---|
| Login | Sign In | handleSubmit → login() | POST /auth/login | token stored, redirect to / | PASS (test) |
| Login | show/hide password | setShowPassword | — (local) | toggles input type | PASS |
| Dashboard | "Open Payment Hub →" | Link | route /hub | Hub page opens | PASS |
| Merchants | Add Merchant | dialog → handleSubmit | POST /merchants | created, list refreshes | PASS (test) |
| Merchants | Edit (row menu) | handleEdit → handleSubmit | PUT /merchants/{id} | updated | PASS |
| Merchants | Delete (row menu) | handleDelete (confirm) | DELETE /merchants/{id} | deleted or 400 w/ dependency message | PASS (test) |
| Merchants | Search box | debounced fetch | GET /merchants?search= | server-side filtered list | PASS |
| Merchants | Status filter / Refresh | fetchMerchants | GET /merchants | filtered list | PASS |
| Merchants | Pagination Prev/Next | setPage | GET /merchants?page= | next page | PASS (test) |
| VAR Sheet | Merchant select | setSelectedMerchant | — | enables upload | PASS |
| VAR Sheet | Upload zone (click/drop) | handleFileUpload | POST /admin/varsheet/upload | uploaded, appears in list | PASS |
| VAR Sheet | Parse PDF | handleParse | POST /admin/varsheet/{id}/parse | parsed fields shown w/ confidence | PASS |
| VAR Sheet | Save Draft | handleSaveParsedData | PUT /admin/varsheet/{id} | ALL 32 fields persist (model test) | PASS (test) |
| VAR Sheet | Create Terminal Profile | handleCreateTerminal | POST /admin/terminals | terminal created | PASS |
| VAR Sheet | 6 tab triggers | Tabs | — | tab switches | PASS |
| Terminals | Add Terminal | dialog → handleSubmit | POST /admin/terminals | created | PASS |
| Terminals | Record Provisioning (row) | handleProvision | POST /admin/terminals/{id}/provision | status → Provisioning Tracked | PASS |
| Terminals | Confirm Live (row) | handleMarkLive | POST /admin/terminals/{id}/mark-live | status → Live (Confirmed) | PASS |
| Terminals | Search / status filter / Refresh | fetchTerminals | GET /admin/terminals | server-side filtered | PASS |
| Terminals | Pagination | setPage | GET /admin/terminals?page= | next page | PASS |
| Transactions | Export CSV | handleExport | GET /reports/export | CSV downloads; truncation warned | PASS |
| Transactions | Date/merchant/status filters, Refresh | fetchTransactions | GET /transactions | filtered w/ full-set summary | PASS |
| Transactions | Pagination | setPage | GET /transactions?page= | next page | PASS |
| Payment Hub | Run Health Checks | fetchStatus(manual) | GET /hub/status?manual=true | live checks table + audit row | PASS (test) |
| Payment Hub | Merchant select (Terminals tab) | fetchHubView | GET /hub/merchants/{id}/hub-view | live Hub profiles/routing | PASS |
| Payment Hub | Ping (per profile) | pingProfile | POST /hub/profiles/{id}/ping | real probe result + audit | PASS (test) |
| Payment Hub | Ping All Profiles | bulkPing | POST /hub/profiles/bulk-ping | bounded fan-out, counts + audit | PASS (test) |
| Payment Hub | Run Readiness Check | runReadiness | GET /hub/merchants/{id}/readiness | PASS/WARN/FAIL/UNKNOWN checks + overall | PASS (test) |
| Payment Hub | Link to Hub / Edit Link → Verify & Save | saveLink | PUT /hub/links/merchants/{id} | verified against live Hub, saved, audited | PASS (test) |
| Payment Hub | Events tab trigger | fetchEvents | GET /hub/events | live stats + undelivered | PASS |
| Payment Hub | 5 tab triggers | Tabs | — | tab switches | PASS |
| Reports | Generate Report | generateReport | GET /reports/transactions or /batches | summary + charts + table | PASS |
| Reports | Export CSV | handleExport | GET /reports/export | CSV downloads | PASS |
| Reports | Date/merchant filters, tab triggers | state | — | applied on Generate | PASS |
| Users | Add User | dialog → handleSubmit | POST /auth/register | created (SUPER_ADMIN only) | PASS (test) |
| Users | Role select (per row) | handleRoleChange | PUT /users/{id}/role | role updated + audit | PASS (test) |
| Users | Activate/Deactivate (per row) | handleStatusChange | PUT /users/{id}/status | status flips; self blocked | PASS (test) |
| Users | Search / Refresh / Pagination | fetchUsers | GET /users | server-side | PASS |
| System Logs | Export Logs | handleExport | GET /logs/export | CSV downloads (audited) | PASS |
| System Logs | Apply filters | applyFilters | GET /logs | filtered page 1 | PASS |
| System Logs | Page-filter search box | client filter (labeled "Filter loaded page...") | — | filters visible rows only, honestly labeled | PASS |
| System Logs | Pagination | setPage | GET /logs?page= | next page | PASS |
| Shell | 9 nav links | NavLink | routes | page renders | PASS (smoke test) |
| Shell | Mobile menu open/close | setSidebarOpen | — | sidebar toggles | PASS |
| Shell | User menu → Logout | logout() | — (clears token) | redirected to login | PASS |

Acceptance: **zero dead visible controls** — every control above has a real handler and a real
backend effect or navigation. The smoke test suite additionally asserts the removed dead controls
cannot silently return (no `href="#"`, no Settings/Virtual Terminal/Affiliates nav entries).
