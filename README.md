# Block29 Admin

Internal company admin for the Block29 ecosystem:

- **AsterPOS** (asterpos.com) — point of sale platform
- **Chain29** (chain29.com) — restaurant chain app
- **Agent9** (agent9.com) — voice AI engine

Manages merchants, TSYS VAR sheet intake, terminal profiles and provisioning status, transactions, reports, admin users/roles, the audit trail, and a live **Payment Hub operations console** (health checks, real terminal pings, go-live readiness, Hub mappings) against the AsterPOS Payment Hub. See `PAYMENT_HUB_ADMIN_API_MAP.md`, `ADMIN_RBAC_MATRIX.md`, and `ADMIN_FINAL_AUDIT.md`.

Run migrations in `backend/migrations/` (001–004, manual, ordered) against the live MySQL before deploying this branch.

## Stack

- **Backend:** FastAPI + SQLAlchemy (async) + MySQL — `backend/server.py`
- **Frontend:** React (CRA/craco) + Tailwind + shadcn components — `frontend/`

## Running

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

Required environment variables (e.g. in `backend/.env`):

| Variable | Purpose |
|---|---|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | MySQL connection |
| `JWT_SECRET` | **Required.** Token signing secret — server refuses to start without it |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Optional. Seeds the first SUPER_ADMIN on startup if that email doesn't exist |
| `CORS_ORIGINS` | Comma-separated allowed origins (defaults to `*` with a startup warning — set it in production) |
| `PAYMENT_HUB_URL` | AsterPOS Payment Hub base URL (e.g. `https://www.123cents.com`) |
| `PAYMENT_HUB_ADMIN_KEY` | Hub `ADMIN_API_KEY`; sent server-to-server as `X-Admin-Key`, never to the browser |
| `PAYMENT_HUB_ENV` | Environment label shown in the Hub console (`production` / `staging`) |
| `PAYMENT_HUB_TIMEOUT_SECONDS` | Hub call timeout (default 10) |

Frontend:

```bash
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

## Roles

`SUPER_ADMIN` (everything, user management, logs), `OPERATIONS` (merchants, VAR sheets, terminals), `SUPPORT` (transactions, reports), `READ_ONLY` (view).

## Notes

- Terminal "provision" / "mark live" are **manual status tracking** — no processor API is called yet. Real gateway provisioning (Clover / Dejavoo / Valor) is a planned build; see `ADMIN_AUDIT.md`.
- Payment processing (virtual terminal) was removed on purpose: the previous implementation simulated approvals and must not exist until a real gateway integration lands.
- `ADMIN_AUDIT.md` holds the full site audit and the remaining build-or-delete decisions.
