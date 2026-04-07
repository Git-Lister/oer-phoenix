# Staff Dashboard

This document describes the purpose and current status of the OER_Phoenix staff dashboard.

The dashboard is designed as a librarian‑friendly interface for day‑to‑day operations, separate from the full‑power Django admin.

## Goals

- Provide a clear overview of sources, harvests, and enrichment status.  
- Offer one‑click access to common actions.  
- Reduce the need for staff to use Django admin for routine tasks.

## Main views

### 1. Sources overview

Shows configured sources and their status.

Typical information:

- Source name and type  
- Last harvest date and outcome  
- Next scheduled harvest (if applicable)  
- Quick actions to test or run a harvest

### 2. Harvest jobs

Lists recent harvest jobs with high‑level status.

Typical information:

- Source  
- Start and end time  
- Records found / created / updated / failed  
- Status (success, partial, failed)

### 3. Enrichment and embeddings

Shows enrichment and embedding status across records.

Typical information:

- Number of records enriched  
- Number of records with embeddings  
- Pending jobs  
- Buttons to trigger enrichment or embedding for selected sets of records

### 4. Quality and review

Supports triage and review workflows.

Typical information:

- Distribution of quality scores  
- Lists of records that may need human review  
- Filters for incomplete or questionable metadata

## Permissions

The dashboard is intended for authenticated staff users.

Access is typically restricted by:

- Django user groups  
- Permissions assigned to roles

## Relationship to Django admin

- Use **Django admin** for deep configuration, debugging, and advanced actions.  
- Use the **staff dashboard** for routine monitoring and operations.

## Status

The dashboard is under active development.

Users should expect:

- Layout and content to evolve.  
- Additional views and filters over time.

## Related documents

- `README.md`  
- `docs/architecture.md`  
- `docs/enrichment.md`  
- `docs/talis-workflows.md`