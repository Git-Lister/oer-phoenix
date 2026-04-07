# Deployment

This document describes common deployment patterns for OER_Phoenix in an academic library context.

It is written for technical staff who may not work with Django every day but are comfortable with Docker, basic networking, and institutional IT processes.

## Overview

OER_Phoenix can run in two main profiles:

- **Minimal profile** – harvesting, storage, and keyword search only.  
- **Full profile** – minimal profile plus optional embeddings, AI‑assisted enrichment, and RAG‑style tools for staff.

Both profiles share the same core stack:

- Django web application  
- PostgreSQL database (with optional vector extensions)  
- Redis (for Celery and caching)  
- Celery worker(s) for background jobs  
- Optional: embedding and LLM backends

## 1. Local development

Use this when exploring OER_Phoenix, testing harvests, or developing new features.

### Requirements

- Docker and Docker Compose  
- Git  
- 4–8 GB RAM

### Steps

1. Clone the repository.  
2. Create a `.env` file based on `.env.example`.  
3. Start the stack with `docker compose up -d`.  
4. Run migrations and create an admin user.  
5. Access the site at `http://localhost:8000/`.

See the README for the exact commands.

## 2. Minimal profile deployment

Use this when you want a simple, low‑risk deployment without AI services.

### Features included

- Harvesting and ingestion  
- Storage in PostgreSQL  
- Keyword and faceted search  
- Django admin  
- Staff dashboard (for supported features)

### Typical components

- `web` – Django + Gunicorn  
- `db` – PostgreSQL  
- `redis` – Redis for Celery  
- `worker` – Celery worker  
- Optional: `nginx` or another reverse proxy in front

### Notes

- No embeddings or LLM services are required.  
- Enrichment is limited to rules‑based or non‑LLM processing.  
- Suitable for pilots, low‑resource environments, or institutions with strict AI policies.

## 3. Full profile deployment

Use this when you want semantic search, AI‑assisted enrichment, and optional RAG tools.

### Features included

Everything in the minimal profile, plus:

- Embeddings for semantic search  
- AI‑assisted enrichment  
- Optional staff‑only RAG tools

### Additional components

Depending on your choices:

- Embedding service (self‑hosted or external)  
- LLM service (self‑hosted or external)  
- Additional Celery workers for heavier workloads

### Notes

- Requires careful review of data protection and AI provider policies.  
- Strongly recommended to use separate environment variables and secrets for API keys.  
- Monitoring and logging become more important as complexity increases.

## 4. Example topologies

### Single‑node deployment

Run all services on a single VM or host, using Docker Compose.

Pros:

- Simple to understand  
- Easy to update and roll back

Cons:

- Limited scalability  
- Single point of failure

### Multi‑node deployment

Separate database, cache, and application servers.

Pros:

- Better performance and resilience  
- Easier to scale workers separately from the web tier

Cons:

- More moving parts  
- Requires more coordination with institutional IT

## 5. Configuration basics

Key configuration areas include:

- Database credentials and connection settings  
- Django `SECRET_KEY`  
- Allowed hosts and HTTPS settings  
- Redis and Celery configuration  
- Enrichment and embedding backend settings

These are typically provided via environment variables or Docker Compose `.env` files.

## 6. Upgrades and maintenance

Recommended practices:

- Run database migrations as part of each upgrade.  
- Keep Docker images and base OS packages patched.  
- Monitor logs for harvest errors and failed jobs.  
- Periodically review source configurations and credentials.

## 7. Institutional considerations

Before going live, coordinate with:

- Information security / data protection teams  
- Library leadership  
- Learning technology teams  
- IT infrastructure teams

Topics to cover:

- Where the system will run (on‑premises vs cloud)  
- Backup and recovery  
- Access control and authentication  
- AI provider policies (if used)

## 8. Related documents

- `README.md`  
- `docs/goals-2026.md`  
- `docs/architecture.md`  
- `docs/enrichment.md`  
- `docs/security.md`