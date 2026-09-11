# Block29 Admin — Full Site Audit & Fix Plan

Audited: 2026-09-11 · Scope: entire repo (`backend/server.py`, all 13 frontend pages, layout, auth, dependencies)

## Executive summary

The admin is a mix of three kinds of features:

1. **Real, working features** — Merchants CRUD, Users & Roles, VAR sheet upload/parse, Terminal profiles, System Logs, Reports mechanics. These are worth keeping.
2. **Fake / simulated features that look real** — Virtual Terminal (approvals decided by `random()`, no gateway), Block29 Gateway provisioning (writes a DB row and stops), Settlement report fees (invented 2.9% + $0.30), Dashboard "Transactions Overview" chart (hardcoded numbers), Login page stats (500+ merchants / $2.5M daily — fiction).
3. **Dead features** — Settings page (nothing saves), several buttons with no handler, pairing tokens nothing ever consumes, a RISK role no endpoint checks, 34 of 46 UI components and a dozen+ npm/pip dependencies used nowhere.

There are also **3 critical security holes** (unauthenticated admin registration, raw card data accepted by a fake processor, hardcoded JWT secret) and the entire app is still branded **SalonBookin** — including the seeded `admin@salonbookin.com / admin123` account advertised on the login screen.

---

## 🔴 Critical security issues (fix before anything else)

| # | Issue | Where | Detail |
|---|-------|-------|--------|
| S1 | **Anyone can create a SUPER_ADMIN** | `POST /api/auth/register` (server.py:461) | Endpoint has no auth and accepts `role` in the body. Any person who can reach the API can self-register as SUPER_ADMIN. The Users page uses this endpoint for "Add User", but the backend never checks who is calling. |
| S2 | **Fake processor accepts real card data** | `POST /api/virtual-terminal/process` (server.py:951) | The UI collects full PAN + CVV + expiry and sends it to the server, which "approves" 90% at random and stores expiry, cardholder, last4 in the DB. No gateway is involved. If anyone keys a real card into this, you have PCI exposure with zero benefit. |
| S3 | **Hardcoded JWT secret fallback** | server.py:46 | `'salonbookin-admin-secret-key-2024'` is in the public repo. If `JWT_SECRET` env is unset, anyone can forge admin tokens. |
| S4 | **Default admin + demo credentials on the login screen** | server.py:442, LoginPage.js:295 | `admin@salonbookin.com / admin123` is auto-seeded at startup and printed in a "Demo Credentials" box on the production login page. |
| S5 | **users table schema mismatch** | server.py:444 vs 470/483 | Startup seeds the admin with columns `password_hash`, `business_name`; register/login read/write `password`, `name`. Both cannot match the real MySQL schema — either the seeded admin can't log in or registration is writing to the wrong columns. This needs a look at the live DB and one consistent set of columns. |
| S6 | **Audit trail is mostly blind** | server.py | Only virtual-terminal, refund, tx-create, and exports write audit logs. Merchant create/edit/delete, terminal changes, user creation, and role changes are **not logged** — yet the System Logs page claims "audit trail of all admin actions". `ip_address` is hardcoded `0.0.0.0`. |

---

## Page-by-page audit

Verdicts: ✅ KEEP (works) · 🔧 FIX (keep, needs repair) · ⚖️ DECIDE (half-built or fake — build for real or delete) · 🗑 DELETE

### 1. Login — 🔧 FIX
- Login itself works (JWT via `/auth/login`).
- **Fake:** left-panel stats "500+ Active Merchants, 1,200+ Terminals, $2.5M Processed Daily" are hardcoded fiction; App Store / Google Play badges link to nothing (there is no app).
- **Dead:** "Forgot Password?" links to `#` (no reset flow exists anywhere); "Remember me" checkbox is wired to nothing.
- **Wrong:** SalonBookin logo (hotlinked from `customer-assets.emergentagent.com`), SalonBookin name, demo credentials box (S4).
- **Recommend:** keep the page; strip fake stats, badges, demo creds, dead links; rebrand Block29; host the logo locally.

### 2. Dashboard — 🔧 FIX
- Stats cards (merchants / terminals / transactions / pending) are real, from `/dashboard/stats`.
- **Fake:** "Transactions Overview" bar chart is hardcoded `Week 1: 45, Week 2: 52, Week 3: 38, Week 4: 65` regardless of reality (Dashboard.js:44). "This month" label sits on an **all-time** count. "Last updated" is just the page-render time.
- Merchant pie chart and Recent Activity are real.
- **Recommend:** keep; replace the fake chart with real weekly aggregates (backend already returns 30 recent transactions; better: a small `/dashboard/timeseries` query), fix labels.

### 3. Merchants — ✅ KEEP
- The most complete page: create/edit/delete/search/filter all work against real endpoints with role checks.
- Minor: delete is a hard delete with no check for attached terminals/transactions (orphans data); no audit logging (S6); search is applied both server- and client-side (harmless).
- **Recommend:** keep as-is; add delete safeguard + audit logs.

### 4. VAR Sheet Setup — 🔧 FIX
- Upload → parse (PyPDF2 + regex) → review → "Create Terminal Profile" flow genuinely works.
- **Broken – silent data loss:** the edit form shows ~25 fields, but `PUT /admin/varsheet/{id}` validates against a model with only 13 fields. Everything on the **Location tab**, plus `industry_type`, `visa_mcc`, `terminal_status`, `v_number_secondary`, `location_number`, `host_capture_participant`, `edc_primary/secondary`, `reimbursement_att`, is **silently discarded on save** — the user sees "Changes saved" but the values are gone on reload.
- **Dead:** "Mark Live" button has no onClick handler at all (VarSheetPage.js:696).
- **Inconsistent:** page says TSYS, creates terminals with `provider: 'tsys'`; the Terminals page creates `provider: 'luqra'`; Settings page says "Provider: Luqra"; requirements.md says Luqra. Pick one.
- **Recommend:** keep — this is core ops tooling; fix the save model, wire or remove Mark Live, settle the provider naming.

### 5. Terminals & Devices — 🔧 FIX
- Terminal CRUD and the draft → provisioned → live status workflow work, **but "provision" only flips a DB status field** — no processor is contacted. Fine as a manual tracking tool, misleading as automation.
- **Dead-end:** "Generate Pairing Token" creates a token in `pos_terminal_links`… and no endpoint anywhere reads, validates, or redeems it. Unless the POS app reads that table directly, this is a feature to nowhere.
- Filter offers a "ready" status that no code ever sets. Provider mismatch ('luqra' here vs 'tsys' from VAR page).
- **Recommend:** keep as the terminal registry; decide whether pairing tokens have a consumer (POS side) — if not, remove; align provider values.

### 6. Virtual Terminal — ⚖️ DECIDE (currently: delete or disable)
- Polished UI, completely fake backend: approval is `random.random() > 0.1` (server.py:972), auth codes are random UUID fragments, "Test Card 4111…" tips are shown, and it accepts **any** card number.
- Fake transactions land in the same `transactions` table your real Transactions page, Reports, batches, and settlement read from — **it pollutes every report**.
- Refund endpoint is equally simulated. Security issue S2 applies.
- **Recommend:** either integrate a real gateway (this is a major project) or **remove the page + endpoints now**. Don't leave a random-number payment simulator in a production admin.

### 7. Transactions — 🔧 FIX
- Real listing with merchant/status filters; summary cards computed from data. Works.
- **Dead:** the "Export" button has no onClick handler (TransactionsPage.js:78) — Reports' export does work, this one is decorative.
- Backend supports date-range filtering; the UI never exposes it. Title says "Transactions & Batches"; there are no batches here (they're on Reports).
- Data is currently polluted by Virtual Terminal's fake transactions.
- **Recommend:** keep; wire or remove the Export button, add date filters, rename to "Transactions".

### 8. Reports — 🔧 FIX / ⚖️ partly
- Transaction and Batch reports work mechanically (real queries, real charts, working CSV export).
- **Fiction:** the Settlement report's fees are hardcoded `2.9% + $0.30` per transaction (server.py:1174) — not your actual pricing, not per-merchant, not from any processor. The "Net Payout" it shows is an invention.
- All three reports are only as real as the transactions table (see Virtual Terminal pollution).
- **Recommend:** keep Transaction + Batch reports; either feed Settlement a real fee schedule or remove that tab until settlement data actually exists.

### 9. Block29 Gateway — ⚖️ DECIDE (currently a stub)
- "New Provision" writes a row with status `submitted` and **nothing else ever happens** — no Clover/Dejavoo/Valor API call, no status transitions. The UI renders icons for `completed`/`failed` states that can never occur.
- The "Routing Architecture" diagram is a static picture.
- Overlaps two other provisioning features (Terminals' provision button, VAR sheet → terminal), so you have **three** half-provisioning flows and zero real ones.
- **Recommend:** decide the real provisioning story. If Block29 gateway integration is on the roadmap, this page is the skeleton for it; if not, delete the page + 2 endpoints + table and keep provisioning state on Terminals only.

### 10. Affiliates & Agents — ⚖️ DECIDE (half-built)
- Assignment create/list works, but:
  - `GET /agents` returns **every user in the users table** — there is no agent entity or role, so your admin staff show up as "agents" in the dropdown.
  - Commission rate is stored and then **never used** — no calculation, no payouts, no reporting, no edit/delete of assignments.
- **Recommend:** if agent commissions are a real business need, this needs an actual agent model + commission engine (design work). Otherwise delete the page + 3 endpoints + table until it's needed.

### 11. Users & Roles — 🔧 FIX
- List users, create user, change role — all work for SUPER_ADMIN.
- Rides on the unauthenticated register endpoint (S1). No deactivate/delete user. **RISK role exists in the UI and role list but no backend endpoint ever grants it anything** — it's READ_ONLY with a scarier badge. Role changes aren't audit-logged.
- **Recommend:** keep; secure register, add deactivate (schema already has `is_active`), drop RISK or give it meaning, log role changes.

### 12. System Logs — 🔧 FIX
- Viewer, filters, and CSV export all work.
- But the underlying audit trail only covers 4 action types (S6); the UI defines colors for LOGIN / UPLOAD / PROVISION actions the backend never writes; IP is always 0.0.0.0; log listing has no pagination beyond a limit.
- **Recommend:** keep the page; expand `create_audit_log` calls to all mutating endpoints and capture the real client IP.

### 13. Settings — 🗑 DELETE (or rebuild minimal)
- **100% non-functional.** "Save Changes" shows a success toast without calling any API (SettingsPage.js:14). There is no backend endpoint for profile update, password change, or any setting.
- Notification switches, **Two-Factor Auth switch**, session-timeout switch — all placebo. A fake 2FA toggle in an admin for payment operations is worse than none.
- System info card hardcodes "Environment: Production" and "Provider: Luqra".
- **Recommend:** delete the page now; later rebuild as just "change my password" (one real endpoint) if wanted.

### Layout / shell — 🔧 FIX
- Notification bell is decorative (static red dot, no click handler, no notifications system). Header dropdown "Settings" item has an **empty** onClick. SalonBookin branding + hotlinked logo.
- **Recommend:** remove the bell (or hide until a notifications feature exists), fix/remove the menu item, rebrand.

---

## Cross-cutting cleanup

- **Branding:** "SalonBookin" appears in the API title, seeded admin, JWT secret, login page, sidebar, and README/requirements docs. The logo is hotlinked from an external CDN (`customer-assets.emergentagent.com`) that can vanish. Rebrand to Block29, host assets locally.
- **Backend deps (`requirements.txt`):** contains MongoDB drivers (`motor`, `pymongo` — app is MySQL), `boto3`, `pandas`, `numpy`, `jq`, `typer`, `rich`, `python-jose` (duplicates PyJWT), `passlib` (bcrypt is used directly), `databases`, `s5cmd`, plus dev tools pinned as prod deps. Roughly half the file is unused.
- **Frontend deps:** `react-hook-form`, `zod`, `date-fns`, `uuid`, `@hookform/resolvers` are used nowhere; `embla-carousel`, `input-otp`, `cmdk`, `vaul`, `react-day-picker`, `react-resizable-panels`, `next-themes` are only referenced by unused shadcn stubs.
- **UI components:** 46 shadcn components vendored, **12 used**. Delete the other 34 (they can be re-generated any time).
- **Dead code/docs:** `App.css` still contains create-react-app logo-spinner boilerplate; `requirements.md` describes a "FastAPI and MongoDB" SalonBookin platform (stale); README is empty boilerplate.
- **Roles:** backend permission checks use only SUPER_ADMIN / OPERATIONS / SUPPORT. RISK ≈ READ_ONLY in practice.

---

## Proposed fix plan

### Phase 0 — Security hotfix (do first, small)
1. Lock down `/auth/register`: require SUPER_ADMIN (it's only called from the Users page anyway); never accept role escalation unauthenticated.
2. Remove the JWT secret fallback — fail hard if `JWT_SECRET` is unset.
3. Remove the demo-credentials box; change/remove the seeded `admin123` account.
4. Resolve the users-table column mismatch (S5) against the live schema.
5. Disable the Virtual Terminal processing endpoint until a decision is made (S2).

### Phase 1 — Delete dead weight (small, no product decisions needed)
1. Delete Settings page (route, nav item, file).
2. Remove fake Dashboard chart data; fake login stats/badges/dead links; dead Export button on Transactions; dead Mark Live button on VAR page (or wire it — see Phase 2); decorative notification bell; empty Settings menu item.
3. Purge unused UI components (34), unused frontend deps, unused pip deps, CRA boilerplate CSS, stale docs.

### Phase 2 — Repair the keepers (medium)
1. VAR sheet: extend `VarSheetParsedData` so all edited fields persist; wire Mark Live to the terminal it created; unify provider naming (TSYS vs Luqra).
2. Audit logging on every mutating endpoint + real client IP; System Logs then shows a true trail.
3. Dashboard: real weekly transaction aggregates; correct labels.
4. Transactions: date-range filter UI, working export (reuse the Reports export), rename page.
5. Users: deactivate user; audit role changes; drop or implement RISK.
6. Merchants: guard delete when terminals/transactions exist.
7. Rebrand everything to Block29; local logo asset.

### Phase 3 — Decide-and-build (needs your product decisions)
| Feature | Option A (build) | Option B (delete) |
|---|---|---|
| Virtual Terminal | Integrate a real gateway (major project; PCI scope) | Remove page + endpoints; purge fake transactions from DB |
| Block29 Gateway | Real Clover/Dejavoo/Valor provisioning APIs + status webhooks | Remove page/endpoints/table; keep Terminals as the single provisioning tracker |
| Affiliates & Agents | Real agent entity, commission calculation, payout reports | Remove until needed |
| Settlement report | Per-merchant fee schedule + real settlement data | Remove the tab; keep Transaction & Batch reports |
| Pairing tokens | Build/connect the POS redemption endpoint | Remove token generation |

### Phase 4 — Hardening (after the above)
- Rate limiting on login, token refresh/expiry handling in the frontend (currently a 24 h token that dies silently), pagination on large tables, and a real password-reset flow if wanted.

**Suggested order of effort:** Phase 0 (hours) → Phase 1 (hours) → Phase 2 (a few days) → Phase 3 per your decisions.
