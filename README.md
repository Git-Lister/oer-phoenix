# OER Rebirth

> A Django-based OER harvesting, enrichment, and search platform with semantic embeddings and AI-powered discovery.

This repository contains a complete platform for harvesting, enriching, and searching Open Educational Resources (OER). The project uses Django, PostgreSQL with pgvector, Celery async workers, and a suite of harvesters (OAI-PMH, MARCXML, CSV, REST API).

**Status:** Production-ready. Latest session completed description enrichment pipeline, admin QOL improvements, and enhanced search interface.

---

## Features

- **Multi-format harvesting** – OAI-PMH, MARCXML, CSV, REST API integrations
- **Semantic search** – Hybrid keyword + vector similarity on pgvector
- **Description enrichment** – Auto-fetch and replace boilerplate descriptions via Celery
- **Admin dashboard** – Filter by embedding status, view resource counts
- **Query AI** – RAG-powered question answering over resource collection
- **Quality scoring** – Automated metadata quality assessment
- **Async processing** – Celery tasks for harvests, enrichment, and indexing

---

## Prerequisites

- Docker & Docker Compose (recommended: Docker Compose v2; use `docker compose`)
- Git
- For local development: Python 3.11+ (Docker image uses 3.12)

---

## Quick Start (Docker)

1. Clone the repository:

```bash
git clone <repo-url>
cd OER_Rebirth
cp .env.example .env
# Edit .env as needed (see .env.example keys)
```

2. Build and start:

```bash
docker compose up --build -d
```

3. Follow logs while the containers start:

```bash
docker compose logs -f web
```

Notes:
- The `web` container's `docker-entrypoint.sh` waits for the DB, creates the
   database if missing, enables the Postgres `vector` extension, runs
   migrations, and creates a default superuser `admin`/`adminpass` if necessary.

---

## Environment variables (important)

The project uses a `.env` file. A complete example is provided in `.env.example`.
Key variables you will commonly set:

- `DJANGO_SECRET_KEY` — Django secret key.
- `DJANGO_DEBUG` — `True` / `False` for local dev vs production.

# Database
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — used by Django.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` — used by the DB
   container during first-time initialization (these often mirror the `DB_*`
   values but are read by the Postgres image).

# Celery / Redis
- `CELERY_BROKER_URL` — e.g. `redis://redis:6379/0` (recommended when using
   the provided `redis` service in `docker-compose.yml`).
- `CELERY_RESULT_BACKEND` — e.g. `redis://redis:6379/1`.

# Local LLM / AI enrichment
- `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_TIMEOUT` — URL and model for
   any local model used for enrichment. When using Docker Desktop and running
   an LLM on the host, use `http://host.docker.internal:<port>` in the `.env`.
- `ENABLE_LLM_ENRICHMENT` — set `False` by default unless you have an LLM
   available. Installing AI deps (torch, transformers) is optional and
   recommended only for users who enable enrichment.

---

## First-run checklist (after `docker compose up`)

1. Visit: http://localhost:8000/ (admin at `/admin/`).
2. Default admin user: `admin` / `adminpass` (created by entrypoint if missing).
    Please change the password immediately.
3. Add an OER source in the admin and run a harvest (see management commands).

---

## Management commands (run inside the `web` container)

Open a shell in the web container:

```bash
docker compose exec web bash
```

Common commands (exact names present under `resources/management/commands`):

- `python manage.py fetch_oer` — run harvests (see command help for args).
- `python manage.py normalise_resource_type` — normalise legacy resource types.
- `python manage.py enrich_subjects` — run subject enrichment/backfill jobs.
- `python manage.py export_talis` — export resources to Talis (requires creds).
- `python manage.py reindex_qdrant` — reindex into Qdrant (if used).
- `python manage.py apply_subject_itemtypes` — apply item type mappings.
- `python manage.py backfill_subjects` — backfill subject data.

Use `python manage.py help <command>` to view usage for each command.

---

## Celery / background tasks

The Compose file includes `celery` and `celery-beat` services. Ensure
`CELERY_BROKER_URL` in `.env` points to Redis when using the bundled Redis
service. Example values are present in `.env.example`.

---

## Optional services

- Qdrant: exposed on port `6333` in `docker-compose.yml` when enabled.
- pgAdmin: exposed on port `8080` (useful for inspecting the Postgres DB).

---

## Troubleshooting

- Database connection errors: verify `.env` DB_* values and that the `db`
   container is healthy (`docker compose ps` / `docker compose logs db`).
---

## Architecture

**Web (Django)** → REST API, admin interface, dashboard, search views

**Database (PostgreSQL + pgvector)** → OERResource, OERSource, task metadata, embeddings

**Celery (async queue)** → Description enrichment, embedding generation, quality scoring

**Search Engine** → Hybrid keyword + semantic search, ranking

**RAG** → LLM integration for question answering with citations

See [docs/](docs/) for detailed architecture diagrams and data flows.

---

## Key Commands

```bash
# Start full stack
docker compose up -d

# Harvest from a source
docker compose exec web python manage.py fetch_oer --source doab --limit 100

# Backfill descriptions (preview)
docker compose exec web python manage.py backfill_descriptions_from_url \
  --preview --limit 50

# Monitor Celery
docker compose logs -f celery

# Create superuser
docker compose exec web python manage.py createsuperuser

# Access dashboard
open http://localhost:8000/home/
open http://localhost:8000/admin/
```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Harvest not starting | `docker compose logs web \| findstr "fetch_oer"` |
| Celery tasks failing | `docker compose logs celery` and check Redis connectivity |
| Description enrichment slow | Verify `CELERY_BROKER_URL` in `.env` points to running Redis |
| Search returning no results | Check pgvector extension: `docker compose exec db psql -c "CREATE EXTENSION IF EXISTS vector;"` |
| Admin page error | Run migrations: `docker compose exec web python manage.py migrate` |

---

## Further Documentation

- **[docs/deployment_verification_checklist.md](docs/deployment_verification_checklist.md)** – Pre-production checks and verification commands
- **[docs/description_enrichment_implementation.md](docs/description_enrichment_implementation.md)** – Description enrichment pipeline design and API
- **[docs/description_enrichment_quickstart.md](docs/description_enrichment_quickstart.md)** – 5-minute enrichment test walkthrough
- **[docs/session_complete_summary.md](docs/session_complete_summary.md)** – Historical development notes for current phase

---

## Contributing

- Fork, branch, and open a pull request to `main`
- Keep documentation changes in the same PR as related code changes
- Run tests before submitting: `python manage.py test resources`

---

## License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Support

- **Issues:** GitHub Issues tab
- **Docs:** [docs/](docs/) folder
- **Questions:** See troubleshooting table above


