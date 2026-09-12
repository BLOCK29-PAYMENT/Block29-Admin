# Block29 Admin - Requirements & Architecture

## Purpose

Internal company admin for the Block29 ecosystem: **AsterPOS** (asterpos.com, point of sale), **Chain29** (chain29.com, restaurant chain app), and **Agent9** (agent9.com, voice AI engine). It manages merchant processing operations: merchants, TSYS VAR sheet intake, terminal profiles, transactions, reports, admin users and the audit trail.

## Current features

### Authentication & authorization
- JWT-based auth; `JWT_SECRET` env var is required (no default).
- Roles: `SUPER_ADMIN`, `OPERATIONS`, `SUPPORT`, `READ_ONLY`.
- User creation is SUPER_ADMIN-only (`POST /api/auth/register` requires auth).
- Optional first-admin seeding via `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars.
- Users can be deactivated (`is_active`); deactivated users cannot log in.

### Dashboard
- Live counts (merchants, terminals, transactions, pending review).
- Real last-4-weeks transaction chart, merchant status pie, recent activity.

### Merchants
- Full CRUD with search/status filters. Deleting a merchant with terminals or transactions is blocked - suspend instead.

### VAR Sheet Setup (TSYS)
- PDF upload, regex extraction, editable review form (all fields persist), terminal profile creation.

### Terminals & Devices
- Terminal registry with manual status workflow: draft → provisioned → live.
- NOTE: status changes are manual tracking only - no processor API is called yet.

### Transactions & Reports
- Transaction listing with merchant/status/date filters and CSV export.
- Transaction and batch (daily settlement trend) reports.

### System Logs
- Audit trail covering login, create/update/delete on merchants/terminals/users, VAR sheet upload/parse/update, terminal provision/mark-live, and exports, with real client IPs. CSV export.

## Removed in the 2026-09 cleanup (see ADMIN_AUDIT.md)

- **Virtual Terminal** - simulated approvals (`random()`), accepted real card data with no gateway. Must not return until a real payment gateway integration exists.
- **Block29 Gateway page** - provisioning stub that never called any processor.
- **Affiliates & Agents** - half-built; no agent entity or commission engine.
- **Settlement report** - fees were hardcoded fiction (2.9% + $0.30).
- **Settings page** - saved nothing; placebo 2FA toggle.
- **Pairing tokens** - generated but nothing ever redeemed them.
- **RISK role** - was never checked by any endpoint.

## Planned builds (decisions pending)

1. Real gateway provisioning (Clover / Dejavoo / Valor) with status callbacks.
2. Real settlement reporting from processor data + per-merchant fee schedules.
3. Agent/affiliate management with a proper agent entity and commission engine.
4. Terminal pairing with an actual POS-side redemption endpoint.
5. Password reset / change-password flow.
