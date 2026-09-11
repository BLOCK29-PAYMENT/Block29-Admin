# Admin Stabilization Baseline — Re-audit of current branch

Branch: `claude/admin-site-full-audit-tdb6m0` · Re-audited from source, not from the old audit.
Verdicts: KEEP · KEEP + FIX (fixed in this pass) · DELETE (already deleted) · BLOCKED ON EXTERNAL INTEGRATION

## Pre-check: previously completed security fixes — all verified still present

| Fix | Verified at |
|---|---|
| `/auth/register` restricted to SUPER_ADMIN | server.py register endpoint (`Depends(require_roles("SUPER_ADMIN"))`) + test |
| JWT secret required, no fallback | server.py startup guard + test (`missing JWT_SECRET → RuntimeError`) |
| Demo credentials removed | grep: zero `admin123` matches in frontend/backend |
| Seeded admin123 removed | seeding now env-driven (`ADMIN_EMAIL`/`ADMIN_PASSWORD`) |
| Fake Virtual Terminal removed | grep: zero `virtual-terminal` matches; test asserts 404 |
| Block29 stub / Affiliates / Settlement / Settings removed | grep + tests assert 404 |
| VAR sheet save fixed | `VarSheetParsedData` covers all 32 UI fields; test enforces coverage |
| Audit logging expanded + real client IP | `create_audit_log` + contextvar middleware |
| Dashboard real chart | `/dashboard/stats` weekly aggregates |
| Transactions export fixed | working CSV via `/reports/export` |
| User deactivation | `PUT /users/{id}/status` + login block |
| Block29 rebrand (AsterPOS / Chain29 / Agent9) | grep: zero `salonbookin`/`emergentagent` matches |

## Page-by-page baseline

| Page / Feature | Frontend | Backend | DB persists | Real/Fake | Permissions | Audit log | Error handling | Tests | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1. Login | ✅ | ✅ `/auth/login` | users table | REAL | n/a (public) | LOGIN + LOGIN_FAILED | toasts + 401/403/429 | ✅ | KEEP + FIX (rate limiting, failure audit added this pass) |
| 2. Dashboard | ✅ | ✅ `/dashboard/stats` | reads merchants/terminals/transactions | REAL (weekly chart from SQL) | any authenticated | read-only, none | loading/empty | smoke | KEEP |
| 3. Merchants | ✅ | ✅ full CRUD | merchants | REAL | SA/OPS write, all read | CREATE/UPDATE/DELETE | toasts, 400s | ✅ | KEEP + FIX (duplicate check, pagination added this pass) |
| 4. VAR Sheet Setup | ✅ | ✅ upload/parse/save/create-terminal | varsheet_uploads, terminal_profiles | REAL | SA/OPS write | UPLOAD/PARSE/UPDATE | toasts, parse failures surfaced | field-coverage test | KEEP |
| 5. Terminals & Devices | ✅ | ✅ CRUD + status | terminal_profiles | REAL as *internal tracker* — labels made honest this pass ("Provisioning Tracked", "Live (Confirmed)") | SA/OPS write | CREATE/UPDATE/PROVISION/MARK_LIVE | toasts | ✅ | KEEP + FIX |
| 6. Transactions | ✅ | ✅ paginated list + summary | transactions | REAL (fake VT rows identified for cleanup — see migrations/003) | SA/OPS/SUPPORT | EXPORT | toasts, empty state | ✅ | KEEP + FIX (pagination + server-side totals added) |
| 7. Reports | ✅ | ✅ transactions/batches/export | transactions | REAL (settlement fiction already deleted; "Net Settlement" relabeled "Net Total") | SA/OPS/SUPPORT | EXPORT | toasts | ✅ | KEEP + FIX |
| 8. Users & Roles | ✅ | ✅ list/create/role/status | users | REAL | SUPER_ADMIN | CREATE/UPDATE + status | toasts, 403s | ✅ | KEEP + FIX (pagination, password policy added) |
| 9. System Logs | ✅ | ✅ paginated + export | audit_logs | REAL | SUPER_ADMIN | EXPORT (of logs) audited | toasts | ✅ | KEEP + FIX (pagination; page-scoped stats relabeled) |
| 10. App Shell | ✅ | n/a | n/a | REAL (bell removed, dead menu items removed, B29 mark local) | route-guarded | n/a | n/a | smoke | KEEP |
| Payment Hub console | none yet | none yet | Hub-side | — | — | — | — | — | BUILD THIS PASS (see §41–76); real Hub API confirmed in AsterPOSPaymentHub |

## Dead-remnant sweep of removed features

| Remnant | Location | Status |
|---|---|---|
| Virtual Terminal endpoints/UI | — | GONE (tests assert 404) |
| Block29 Gateway stub endpoints/UI | — | GONE |
| Affiliates endpoints/UI | — | GONE |
| Settlement endpoint/tab | — | GONE (only stale *word* "settlement" in two labels — fixed this pass) |
| Settings page / menu entries | — | GONE |
| Notification bell / empty handlers / `href="#"` | — | GONE (grep clean) |
| `pos_terminal_links` table (pairing tokens) | MySQL | ORPHAN — migration `002_drop_removed_feature_tables.sql` |
| `block29_provisions`, `agent_merchants` tables | MySQL | ORPHAN — same migration |
| Fake VT rows in `transactions` | MySQL | Identified by `terminal_id='VIRTUAL'` — migration `003` (owner-reviewed cleanup, NOT automatic) |
| Unused shadcn stubs (34 files), `App.css`, `hooks/use-toast.js` | frontend/src | Present but inert (not imported, not bundled). Deletion blocked by session file-delete permission — flagged for one `git rm` commit |
| `motor`/`pymongo`/`boto3`/etc. pip deps | requirements.txt | GONE (trimmed to runtime deps) |
| Unused npm deps | package.json | GONE (52 → 21) |
