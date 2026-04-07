# Architecture Overview

OER_Phoenix is organised as a modular library platform with three core layers: harvesting and ingestion, indexing and enrichment, and user interfaces.

This document explains the current shape of the system, the intent behind each layer, and how the pieces fit together for library workflows.

## Goals the architecture serves

- Aggregate OER from multiple external sources.
- Preserve provenance and licensing information.
- Make metadata enrichment optional, inspectable, and policy-aware.
- Support librarian and teaching workflows, not just technical administration.
- Allow institutions to run the platform with minimal AI or fuller AI capabilities.

## System layers

### 1. Harvesting and ingestion

This layer discovers, imports, and updates OER records from external sources.

Typical responsibilities:

- Source configuration and presets.
- Protocol-specific harvesting from OAI-PMH, REST APIs, MARCXML, and CSV/KBART.
- Scheduling and queue-based processing.
- Logging, retry handling, and harvest status tracking.

Primary concepts:

- Source
- Harvest job
- Harvest batch
- Raw record
- Normalised record

## 2. Indexing, enrichment, and search

This layer improves records and makes them searchable.

Typical responsibilities:

- Normalising metadata.
- Optional enrichment such as summaries, subject suggestions, and quality scoring.
- Generating embeddings for semantic search when enabled.
- Combining keyword, filter, and similarity search.
- Exposing provenance so users can see what came from source data and what was added later.

Primary concepts:

- Enrichment backend
- Embedding backend
- Search index
- Quality score
- Provenance label

### 3. User interfaces

This layer exposes the system to staff and learners.

Typical responsibilities:

- Django admin for technical configuration.
- Staff dashboard for librarian workflows.
- Discovery UI for learners and teaching staff.
- Staff-only testing tools for optional AI-assisted functions.

Primary concepts:

- Admin interface
- Staff dashboard
- Discovery interface
- Result explanations
- Reading-list export

## Data flow

A typical record moves through the system in this order:

1. A source is configured.
2. A harvest job imports records.
3. Records are normalised and stored.
4. Optional enrichment adds derived metadata.
5. Optional embeddings support semantic search.
6. Search results are presented in the discovery UI.
7. Staff can review, export, or push selected records into other systems.

## Deployment profiles

### Minimal profile

The minimal profile is intended for evaluation, low-resource environments, or institutions that want a non-AI baseline.

Includes:

- Harvesting and ingestion.
- Metadata storage.
- Keyword search.
- Basic admin access.

### Full profile

The full profile adds optional AI-enabled features for institutions that can support them.

Includes:

- Embeddings.
- AI-assisted enrichment.
- Quality scoring.
- Optional retrieve-and-generate workflows.

## Library workflows supported

- Source onboarding and testing.
- Harvest monitoring.
- Metadata review and enrichment.
- Discovery and evaluation of resources.
- Reading-list export and Talis integration.
- Staff review of AI-assisted outputs.

## Design principles

- Keep source metadata separate from derived metadata.
- Make AI optional.
- Expose provenance and explanation where possible.
- Prefer reusable configuration over custom code.
- Keep the stack understandable for library and technical teams.

## Related documents

- `docs/goals-2026.md`
- `docs/enrichment.md`
- `docs/dashboard.md`
- `docs/talis-workflows.md`
- `docs/deployment.md`
- `docs/security.md`
