# Campus Hub Backend

Django + DRF API project (Django 6, Python 3.12).

## Structure
- `backend/` — Django project (apps: `accounts`, `courses`, `attendances`; config in `backend/config/`)
- `AI/` — RAG / chat scripts (separate, not wired into the API)

## Run (dev)
- Workflow `Start application` runs `python manage.py runserver 0.0.0.0:5000` from `backend/`.
- Settings module: `config.settings`, switched by `ENV` env var (`dev` / `prod` / `test`).
- `backend/.env` provides `ENV=dev` and `SECRET_KEY` for local dev. SQLite at `backend/db.sqlite3`.
- Swagger UI served at `/`, schema at `/api/schema/`, API under `/api/v1/`.

## Deployment
- Autoscale target, gunicorn `config.wsgi:application` on port 5000. Build runs migrations.
- Currently uses `ENV=dev` (SQLite). For real production, provision a Postgres DB, set `DATABASE_URL`, and switch deploy command to `ENV=prod`.
