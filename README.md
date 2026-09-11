# Block29 Admin

Internal company admin for the Block29 ecosystem:

- **AsterPOS** (asterpos.com) — point of sale platform
- **Chain29** (chain29.com) — restaurant chain app
- **Agent9** (agent9.com) — voice AI engine

Manages merchants, TSYS VAR sheet intake, terminal profiles and provisioning status, transactions, reports, admin users/roles, and the audit trail.

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
| `CORS_ORIGINS` | Comma-separated allowed origins (defaults to `*`) |

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
