# Fake / Dead Function Report

Full-repo sweep for fake behavior: random results, fake success toasts, hardcoded stats,
placeholder statuses, empty handlers, `href="#"`, UI states the backend can never produce.

Search patterns used: `random`, `toast.success` (verified each fires only after awaited backend
success), `href="#"`, `onClick={() => {}}`, hardcoded numeric literals in stat cards, status
values rendered by UI vs. producible by backend, `Math.random`, `setTimeout`-fake latency.

## Findings fixed in earlier commits of this branch (verified still gone)

| # | File | Feature | Why fake/dead | Action |
|---|---|---|---|---|
| 1 | backend (removed) | Virtual Terminal processing | `random.random() > 0.1` approvals, random auth codes | REMOVED (endpoints + page); test `test_no_random_approval_code_in_backend` guards regression |
| 2 | backend (removed) | Block29 Gateway provisioning | wrote `status='submitted'`, no processor call, UI rendered impossible `completed/failed` states | REMOVED |
| 3 | backend (removed) | Settlement report | hardcoded `2.9% + $0.30` fees | REMOVED |
| 4 | Dashboard.js | Transactions chart | hardcoded Week 1–4 values | FIXED — real SQL weekly aggregates |
| 5 | LoginPage.js | "500+ merchants / $2.5M daily", app-store badges | fiction | REMOVED |
| 6 | LoginPage.js | "Forgot Password?" `href="#"`, "Remember me" | dead link, dead checkbox | REMOVED |
| 7 | SettingsPage.js (removed) | Save/2FA/notification toggles | `toast.success` with no API call | PAGE REMOVED |
| 8 | VarSheetPage.js | "Mark Live" button | no onClick | REMOVED |
| 9 | TransactionsPage.js | "Export" button | no onClick | FIXED — real CSV export |
| 10 | Layout.js | Notification bell + static red dot, header "Settings" item | no notification system, empty handler | REMOVED |
| 11 | TerminalsPage.js | Pairing tokens | generated, never redeemable by anything | REMOVED (UI + endpoint; table drop in migration 002) |
| 12 | UsersPage.js / backend | RISK role | never checked by any endpoint | REMOVED |

## Findings from THIS re-audit (fixed in this pass)

| # | File | Line (pre-fix) | Feature | Why fake/misleading | Action |
|---|---|---|---|---|---|
| 13 | ReportsPage.js | 153 | Page subtitle "Transaction, batch, and settlement reports" | settlement no longer exists | FIXED — honest subtitle |
| 14 | ReportsPage.js / server.py | 391 / 989 | "Net Settlement" summary card | number is net of admin-recorded transactions, not processor settlement | FIXED — renamed "Net Total" (`net_total`) |
| 15 | ReportsPage.js | 422 | "Daily Settlement Trend" chart silently showing only 14 days | scope not stated | FIXED — "Daily Net Trend (last 14 days shown)" |
| 16 | ReportsPage.js | 337 | "Transaction Details (N)" table silently truncated at 100 rows | count implied all rows shown | FIXED — "showing first 100; use Export CSV" caption |
| 17 | TerminalsPage.js | status badges | "Provisioned"/"Live" implied processor activation | only a DB status flip; no processor contact | FIXED — "Provisioning Tracked" / "Live (Confirmed)" labels, actions renamed "Record Provisioning" / "Confirm Live", page note added |
| 18 | TransactionsPage.js | summary cards | totals computed from the loaded rows only | wrong once pagination exists; also mislabeled scope | FIXED — backend computes totals over the full filtered set; cards labeled "(filtered)" |
| 19 | SystemLogsPage.js | stat cards | "Total Logs"/"Today's Activity"/"Active Users" computed from one fetched page | misleading with pagination | FIXED — "Total Logs (filtered)" uses server total; other cards labeled "(this page)"; search relabeled "Filter loaded page..." |
| 20 | Dashboard.js | Transactions card | "This month" on all-time count | wrong scope | FIXED earlier — "All time" |

## Toast audit (frontend-only success check)

Every remaining `toast.success` call fires only after an awaited 2xx backend response:
LoginPage (post-login), MerchantsPage (create/update/delete), VarSheetPage (upload/parse/save/
create-terminal), TerminalsPage (create/provision/mark-live), TransactionsPage (export),
ReportsPage (export), UsersPage (create/role/status), SystemLogsPage (export). No placebo toasts remain.

## Acceptance

Zero known fake production functionality remains in Block29 Admin. Guard tests:
`test_removed_endpoints_are_gone`, `test_no_random_approval_code_in_backend`,
`test_varsheet_model_covers_every_ui_field`, `test_root_is_rebranded`.
