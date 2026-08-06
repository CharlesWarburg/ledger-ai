# Ledger AI

Ledger AI is an early-stage accounting application intended to combine customer, invoice, and payment management with document processing and financial insights. The repository currently contains the project foundation only: a starter web application, a minimal API, and a PostgreSQL development service.

## Tech stack

- Frontend: Next.js 16.2.10, React 19.2.4, TypeScript 5, Tailwind CSS 4
- Backend: Python, FastAPI 0.128.8, SQLAlchemy 2.0.51, Pydantic Settings 2.11.0, Uvicorn 0.39.0
- Database: PostgreSQL 16 with `psycopg2-binary` 2.9.12
- Infrastructure: Docker Compose for the development database
- Migration tooling: Alembic 1.16.5 configured against SQLAlchemy metadata

Direct backend dependencies are pinned in `backend/requirements.txt`.

## Architecture

The repository is split into two applications:

- `frontend/` is a Next.js App Router application. It currently contains the generated single-page starter UI and no API client, application components, state layer, or feature modules.
- `backend/` is a synchronous FastAPI application. Configuration is loaded from `backend/.env`; SQLAlchemy provides an engine, session factory, declarative base, and request-scoped database dependency. The API currently consists of direct route handlers in `app/main.py`.
- PostgreSQL runs separately through the root `docker-compose.yml` and publishes container port `5432` on host port `5433`.

The `api`, `repositories`, `schemas`, and `services` backend directories exist but are empty. No layered business architecture has been implemented yet.

## Features completed

- Next.js project scaffold with TypeScript, ESLint, Tailwind CSS, and the App Router
- FastAPI application scaffold and generated OpenAPI/Swagger documentation
- `GET /health` application health endpoint
- `GET /db-health` database connectivity endpoint
- SQLAlchemy engine, session factory, declarative base, and FastAPI database dependency
- Environment-based backend database URL loading
- Safe environment examples for Docker Compose and the backend
- Alembic migration environment ready for the first model
- Configurable application lifecycle and HTTP access logging
- Docker Compose PostgreSQL service with persistent storage
- User persistence model and initial database migration
- Argon2id password hashing and verification
- Validated registration, login, and safe user-response schemas

Authentication endpoints and security logic are not implemented yet. Customer, invoice, payment, dashboard, upload, AI, and reporting features also remain unstarted.

## Roadmap

Legend: ✅ completed · 🚧 in progress · ⬜ not started

- ✅ Phase 1 — Foundation
  - ✅ Repository
  - ✅ Next.js setup
  - ✅ FastAPI setup
  - ✅ Docker Compose
  - ✅ PostgreSQL service configuration
  - ✅ SQLAlchemy setup
  - ✅ Database connection and health check
  - ✅ Alembic configuration (the first revision will accompany the first model)
  - ✅ Environment configuration
  - ✅ Application logging
- 🚧 Phase 2 — Authentication
  - ✅ User SQLAlchemy model
  - ✅ Initial users-table migration
  - ✅ Password hashing
  - ✅ Authentication request and response schemas
  - ⬜ JWT creation and validation
  - ⬜ Register endpoint
  - ⬜ Login endpoint
  - ⬜ Current user endpoint
  - ⬜ Protected-route dependency
  - 🚧 Roles (stored on users; authorization enforcement not implemented)
- ⬜ Phase 3 — Customers CRUD
- ⬜ Phase 4 — Invoices CRUD, status, VAT, and due dates
- ⬜ Phase 5 — Payments, partial payments, and outstanding balances
- ⬜ Phase 6 — Dashboard metrics, charts, and recent activity
- ⬜ Phase 7 — PDF, image, and receipt uploads
- ⬜ Phase 8 — OCR and AI invoice processing
- ⬜ Phase 9 — AI financial insights
- ⬜ Phase 10 — Natural-language financial assistant
- ⬜ Phase 11 — CSV, PDF, and monthly reporting
- ⬜ Phase 12 — Production infrastructure, workers, reminders, observability, and testing

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the detailed audit, current task, blockers, and technical decisions.

## How to run locally

Prerequisites: Docker with Compose, Node.js/npm, and Python 3.9 or newer. The existing local backend environment uses Python 3.9.

1. Create the local environment files from the committed examples:

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   ```

   Replace `change_me` in both files with the same local PostgreSQL password. The root `.env` configures the PostgreSQL container, while `backend/.env` configures FastAPI, SQLAlchemy, and Alembic. Do not commit either local `.env` file.

2. Start PostgreSQL from the repository root:

   ```bash
   docker compose up -d postgres
   ```

3. Create the backend environment and install the currently required packages:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   The API is available at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

4. In a second terminal, start the frontend:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   The frontend is available at `http://localhost:3000`.

Useful checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/db-health
cd frontend && npm run lint
cd frontend && npm run build
docker compose down
```

The frontend production build currently needs access to Google Fonts because the root layout uses `next/font/google`.

## Folder structure

```text
ledger-ai/
├── backend/
│   ├── alembic/             # Migration environment and future revisions
│   ├── app/
│   │   ├── api/             # Empty placeholder
│   │   ├── core/
│   │   │   ├── config.py    # Pydantic environment settings
│   │   │   └── logging.py   # Application logging configuration
│   │   ├── db/
│   │   │   └── database.py  # SQLAlchemy engine and sessions
│   │   ├── models/
│   │   │   └── user.py      # Empty placeholder
│   │   ├── repositories/    # Empty placeholder
│   │   ├── schemas/         # Empty placeholder
│   │   ├── services/        # Empty placeholder
│   │   └── main.py          # FastAPI app and two health routes
│   ├── .env.example
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── public/              # Generated starter assets
│   └── src/app/             # App Router layout, page, and global CSS
├── docker-compose.yml       # PostgreSQL development service
├── PROJECT_STATUS.md        # Detailed project audit and status
└── README.md
```

Ignored local items such as `backend/.env`, `backend/.venv`, `node_modules`, and `.next` are intentionally omitted.

## Development phases

Phase 1 is complete, and Phase 2 authentication is in progress. The User model, initial migration, Argon2id password hashing, and authentication schemas are complete. The next implementation task is JWT handling, followed by registration, login, current-user lookup, protected routes, and role enforcement.

## Future work

After the foundation is stable, development should follow the ordered roadmap: authentication and authorization; customer, invoice, and payment domains; dashboard and file storage; AI document processing and insights; assistant and reports; then production infrastructure. Cross-cutting work should include API versioning, validation schemas, repository/service boundaries where useful, automated backend and frontend tests, CI, security checks, structured logging, and deployment documentation.
