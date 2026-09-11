# Admin Final Audit — post-stabilization

Branch `claude/admin-site-full-audit-tdb6m0`. Status values: PASS or BLOCKED only.

## Page-by-page

| Page | Visible features | Backend endpoints | DB tables | Auth | Audit | Tests | Real data | Dead buttons | Fake data | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|
| Login | sign-in, show/hide password | /auth/login | users | public + rate limited | LOGIN, LOGIN_FAILED | 5 unit + smoke | ✅ | none | none | **PASS** |
| Dashboard | 4 stat cards, Hub card, weekly chart, status pie, recent activity | /dashboard/stats, /hub/status | merchants, terminal_profiles, transactions | any role | n/a (read) | live + smoke | ✅ (chart = real SQL aggregate) | none | none | **PASS** |
| Merchants | CRUD, search, filter, pagination | 5 endpoints | merchants | SA/OPS write | CREATE/UPDATE/DELETE | 4 unit | ✅ | none | none | **PASS** |
| VAR Sheet Setup | upload, parse, 6-tab review, save, create terminal | 5 endpoints | varsheet_uploads, terminal_profiles | SA/OPS write | UPLOAD/PARSE/UPDATE | field-coverage test | ✅ | none | none | **PASS** |
| Terminals & Devices | registry, honest status workflow, search, pagination | 5 endpoints | terminal_profiles | SA/OPS write | CREATE/UPDATE/PROVISION/MARK_LIVE | live | ✅ (labels state "internal tracking, no processor API") | none | none | **PASS** |
| Transactions | filters, date range, pagination, full-set totals, CSV export | /transactions, /reports/export | transactions | SA/OPS/SUPPORT | EXPORT | unit + live | ✅ (legacy fake VT rows identified: `terminal_id='VIRTUAL'`; owner-reviewed cleanup in migrations/003) | none | none (pending row cleanup, labeled) | **PASS** |
| Payment Hub | live health checks, merchant hub-view, real device pings, bulk ping, go-live readiness, verified mappings, event feed | 9 /hub endpoints → live Hub APIs | hub_merchant_links, hub_terminal_links (+ Hub-side) | RBAC per matrix | HUB_HEALTH_CHECK, TERMINAL_PING, TERMINAL_BULK_PING, READINESS_CHECK, MERCHANT_HUB_LINK, TERMINAL_HUB_LINK | 11 unit | ✅ — every result from a live Hub/device response; UNKNOWN/NOT CONFIGURED shown honestly | none | none | **PASS** (runtime results BLOCKED until `PAYMENT_HUB_URL`/`PAYMENT_HUB_ADMIN_KEY` are set in deployment — the page says so itself) |
| Reports | transaction + daily batch reports, charts, CSV export | 3 endpoints | transactions | SA/OPS/SUPPORT | EXPORT | live | ✅ ("Net Total", truncation labeled) | none | none | **PASS** |
| Users & Roles | list, create, role change, de/activate, search, pagination | 4 endpoints | users | SUPER_ADMIN | CREATE/UPDATE | 8 unit | ✅ | none | none | **PASS** |
| System Logs | filtered trail, pagination, CSV export | 3 endpoints | audit_logs | SUPER_ADMIN | EXPORT | unit + live | ✅ (real IPs; page-scoped stats labeled) | none | none | **PASS** |
| App shell | nav (9 real pages), user menu, mobile menu | n/a | n/a | route-guarded | n/a | smoke | ✅ | none | none | **PASS** |

## Database table audit

| Table | Owner feature | Read by | Written by | Active | Notes |
|---|---|---|---|---|---|
| users | Users/Auth | login, /users, /auth/me | register, role, status, seed | ✅ | canonical schema documented in migrations/001 (`is_active` migration) |
| merchants | Merchants | 6 pages | merchant CRUD | ✅ | |
| terminal_profiles | Terminals | Terminals, VAR, readiness | terminal CRUD + VAR create | ✅ | |
| varsheet_uploads | VAR Sheet | VAR page, readiness | upload/parse/save | ✅ | |
| transactions | Transactions/Reports | Transactions, Reports, Dashboard | (nothing writes today — POS/Hub ingestion is the future writer) | ✅ read | contains legacy fake VT rows → migrations/003 cleanup plan |
| audit_logs | System Logs | Logs page | every mutating endpoint | ✅ | |
| hub_merchant_links | Payment Hub | hub-view, readiness | link endpoint | ✅ new | migrations/004 |
| hub_terminal_links | Payment Hub | links list | link endpoint (API) | ✅ new | migrations/004 |
| pos_terminal_links | ORPHAN (removed pairing) | nothing | nothing | ❌ | drop in migrations/002 |
| block29_provisions | ORPHAN (removed stub) | nothing | nothing | ❌ | drop in migrations/002 |
| agent_merchants | ORPHAN (removed affiliates) | nothing | nothing | ❌ | drop in migrations/002 |

## Release gate

| Gate | Result |
|---|---|
| Backend tests | **49/49 pass** (`pytest tests/`) |
| Frontend tests | **5/5 pass** (`yarn test`) |
| Production build | **PASS** (`CI=true yarn build` — lint warnings are errors) |
| Backend compile/import | **PASS** (41 routes) |
| Security tests | **PASS** (register lockdown, forged/expired JWT, inactive login, rate limit, removed endpoints stay 404, no `random` payment code, missing JWT_SECRET refuses startup) |
| Fake functionality | **ZERO** (ADMIN_FAKE_FUNCTION_REPORT.md) |
| Dead visible controls | **ZERO** (ADMIN_BUTTON_AUDIT.md) |
| Migrations | 4 SQL migrations written, owner-applied (no auto-run): 001 users.is_active · 002 drop orphan tables · 003 fake-transaction cleanup plan · 004 hub link tables |

## BLOCKED (external / owner action required)

1. **Hub runtime config** — set `PAYMENT_HUB_URL` + `PAYMENT_HUB_ADMIN_KEY` (Hub `ADMIN_API_KEY`) in the admin deployment; until then the Hub console honestly reports NOT CONFIGURED.
2. **Hub-side fixes** (read-only access to that repo here) — see PAYMENT_HUB_ADMIN_API_MAP.md §follow-ups; **#1 (committed production credentials in `ecs-task-definition.json`) is urgent**.
3. **DB migrations** — run 001–004 against the live MySQL (003 is an owner-reviewed cleanup, not automated).
4. **Unused frontend stub deletion** — 34 shadcn stubs + `App.css` + `use-toast.js` are inert but present; bulk file deletion was blocked by session permissions (one `git rm` commit).
5. **Held features (per spec §37)** — Virtual Terminal, settlement engine, affiliates/commissions, POS pairing, 2FA, password reset: not rebuilt, by design.
