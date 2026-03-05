

***

# OER_Phoenix

**OER_Phoenix** is a completely open-source, AI‑powered Open Educational Resources (OER) discovery and curation platform designed for libraries, educators, and learning technologists. It combines traditional metadata harvesting with semantic search, AI‑assisted metadata enrichment, and quality assessment to centralise and streamline the integration of Open Educational Resources into academic institutional workflows. 

> Status: active development. Production use is possible for teams comfortable with Docker, Django, and Postgres.

***

## Table of contents

1. [Project goals](#project-goals)  
2. [Principles](#principles)  
3. [High‑level architecture](#high-level-architecture)  
4. [Key features](#key-features)  
5. [Getting started](#getting-started)  
   - [Prerequisites](#prerequisites)  
   - [Quick start with Docker](#quick-start-with-docker)  
   - [Environments and profiles](#environments-and-profiles)  
6. [Core workflows](#core-workflows)  
   - [Harvesting OER sources](#harvesting-oer-sources)  
   - [Metadata enrichment and embeddings](#metadata-enrichment-and-embeddings)  
   - [Search and discovery](#search-and-discovery)  
   - [Talis / reading‑list workflows](#talis--reading-list-workflows)  
7. [Staff experience](#staff-experience)  
   - [Django admin vs staff dashboard](#django-admin-vs-staff-dashboard)  
8. [Information literacy and AI usage](#information-literacy-and-ai-usage)  
   - [How AI is used](#how-ai-is-used)  
   - [Transparency for learners](#transparency-for-learners)  
9. [Configuration and extensibility](#configuration-and-extensibility)  
10. [Security, privacy, and data protection](#security-privacy-and-data-protection)  
11. [Contributing](#contributing)  
12. [Roadmap](#roadmap)  
13. [About](#about)  
14. [License](#license)

***

## Project goals

OER_Phoenix exists to help institutions:

- Discover and aggregate high‑quality OER from multiple repositories and catalogues.  
- Enrich and normalise metadata to make OER more findable, understandable, and reusable.  
- Support **information literacy**, by exposing how search, AI, and quality judgements are produced rather than hiding them.  


The project is intentionally open‑source to allow scrutiny, adaptation, and contribution by the wider community.

***

## Principles

OER_Phoenix is built around a small set of principles that guide design and implementation.

### 1. Transparency over magic

- Users should be able to see **which fields are original** and **which are AI‑generated or AI‑enriched**.  
- Search results should offer a simple explanation of “why this result?”, including whether ranking was driven by keywords, semantic similarity, or previous interactions. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

### 2. Respect for provenance and licensing

- Original source platforms (e.g. OAPEN, DOAB) are always credited prominently.  
- Licensing information is harvested and preserved; enrichment never changes the licence of a resource.  
- Where possible, outbound links point back to the canonical resource.

### 3. Human judgement first

- AI is used to **support** selection and appraisal, not to replace human judgement.  
- Librarians and educators remain responsible for deciding which resources to recommend, how to contextualise them, and how to interpret AI‑generated summaries or scores.

### 4. Critical engagement with AI

- The interface and documentation encourage users (staff and students) to **question** AI outputs:  
  - Quality scores are explained, not treated as ground truth.  
  - RAG‑style answers are clearly labelled as synthesised and may include citations back to underlying resources.  
- Institutions are encouraged to adapt OER_Phoenix in line with their own AI literacy and academic integrity guidance. 

### 5. Modularity and openness

- Harvesting, indexing/search, and UI are designed as distinct layers so that institutions can reuse or swap out components.  
- Configuration is stored using open formats (e.g. JSON, YAML) where practical.  
- The project aims to remain deployable with standard open‑source tooling (Docker, Postgres, Redis, Celery).

***

## High‑level architecture

At a high level, OER_Phoenix consists of three tightly integrated layers:

1. **Harvesting & ingestion**  
   - Django models for sources, resources, and harvest jobs.  
   - Protocol‑specific harvesters:
     - OAI‑PMH  
     - REST APIs  
     - MARCXML  
     - CSV/KBART  
   - Queue‑based processing via Celery.

2. **Indexing, enrichment, and search**  
   - Postgres plus vector extensions for semantic search.  
   - Enrichment services for:
     - Subject/topic extraction.  
     - AI‑generated summaries.  
     - Quality assessment scores.  
   - Hybrid search engine combining keyword search and vector similarity.

3. **User interfaces**  
   - Django admin for configuration and low‑level management.  
   - Staff dashboard (under development) for common workflows.  
   - Discovery/search UI for learners and teaching staff.

A more detailed architecture diagram lives under `docs/architecture.md`.

***

## Key features

- **Multi‑protocol harvesting**
  - Built‑in support for OAI‑PMH, REST APIs, MARCXML, and CSV/KBART sources.  
  - Configurable presets for commonly used OER repositories to reduce setup time.

- **Metadata enrichment**
  - Optional AI‑assisted summaries and subject classification.  
  - Pluggable enrichment backends (LLM‑based and rules‑based) to suit different institutional policies.

- **Semantic and faceted search**
  - Hybrid search combining keyword, filters, and semantic similarity.  
  - Facets for source, resource type, subject, language, and more. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

- **Quality scoring**
  - `overall_quality_score` field representing metadata richness and other heuristics, with an interpretable banded display (e.g. “limited / good / excellent”). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

- **Reading‑list and export workflows**
  - Talis export and CSV export for integrating with existing reading‑list systems.  
  - Planned: internal “collections” feature for logged‑in users.

***

## Getting started

### Prerequisites

- Docker and Docker Compose  
- Git  
- 4–8 GB RAM recommended for development environment  
- For full AI functionality: access to a supported embedding/LLM backend (self‑hosted or cloud) – see `docs/enrichment.md`. 

### Quick start with Docker

```bash
git clone https://github.com/MMU-Library/OER_Phoenix.git
cd OER_Phoenix

# copy environment template
cp .env.example .env

# start services
docker compose up -d

# run initial migrations and create superuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Then visit `http://localhost:8000/admin/` and log in with your superuser account.

More detailed instructions, including non‑Docker setup, are in `docs/deployment.md`.

### Environments and profiles

OER_Phoenix supports multiple deployment profiles:

- **Minimal profile**  
  Harvesting + basic keyword search, no embeddings or LLM. Use for low‑resource environments or initial evaluation.

- **Full profile**  
  Enables embeddings, AI enrichment, and RAG features. Requires additional services and configuration.

Example Compose files and environment templates for each profile are under `deploy/`.

***

## Core workflows

### Harvesting OER sources

1. Log into Django admin or the staff dashboard.  
2. Choose a **source preset** (e.g. “OAPEN – Books (API)”) or configure a new source manually.  
3. Test the connection to validate endpoints and credentials.  
4. Launch a harvest job and monitor its progress from the Harvest Jobs view. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

Harvest jobs record:

- Source, start/end times, status.  
- Resources found/created/updated/failed.  
- High‑level error summaries plus full log messages for debugging.

### Metadata enrichment and embeddings

After harvesting, you can optionally:

- Run metadata enrichment to generate summaries and enriched subjects.  
- Generate vector embeddings for semantic search.  
- Run quality assessment to assign `overall_quality_score`.

These can be triggered:

- From Django admin via custom actions.  
- From the staff dashboard via dedicated buttons.  
- From scheduled tasks (e.g. nightly Celery beat jobs), if configured. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

### Search and discovery

The discovery UI (non‑admin) allows:

- Keyword and phrase search.  
- Filtering by source, type, subject, language, and date.  
- Sorting by relevance, recency, or quality.  
- Viewing resource details, including clearly labelled AI‑generated fields and links back to the original source. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

A staff‑only RAG test interface lets librarians experiment with LLM‑generated answers summarising sets of search results. This is **not** enabled by default for general users.

### Talis / reading‑list workflows

For institutions using Talis or similar reading‑list systems, OER_Phoenix supports:

- Exporting selected resources as CSV in a Talis‑friendly format.  
- Creating Talis push jobs that send metadata directly to Talis via background tasks. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

Details live in `docs/talis-workflows.md`.

***

## Staff experience

### Django admin vs staff dashboard

OER_Phoenix deliberately distinguishes between:

- **Django admin** – full power, primarily for technical staff:
  - Configure sources and harvester presets.  
  - Inspect raw records and logs.  
  - Run advanced actions and debugging operations. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/112554877/5f388ef1-37c2-4e18-8530-d2d4f538e09c/paste.txt)

- **Staff dashboard** – simplified, librarian‑friendly hub:
  - Overview of sources and their health.  
  - One‑click harvest and test actions.  
  - Enrichment and embedding controls.  
  - High‑level status of processing pipelines.

The staff dashboard is accessible to authenticated staff users with appropriate permissions and is documented in `docs/dashboard.md`.

***

## Information literacy and AI usage

### How AI is used

Depending on configuration, OER_Phoenix may use AI for:

- **Metadata enrichment**  
  - Generating or improving descriptions.  
  - Suggesting subjects, keywords, or levels.

- **Semantic search**  
  - Creating embeddings for titles/descriptions and using them to rerank or expand search results.

- **RAG‑style answers** (optional, staff‑only by default)  
  - Generating natural‑language summaries or overviews based on selected resources.

All AI features are **optional** and can be disabled or replaced with non‑AI alternatives (e.g. rules‑based enrichers).

### Transparency for learners

To support information literacy and critical engagement, OER_Phoenix aims to:

- Clearly label AI‑generated fields on resource pages (e.g. “AI‑generated summary”).  
- Offer a toggle so users can hide/display AI‑generated content.  
- Provide “Why this result?” explanations for search results, indicating:  
  - Which fields matched the query.  
  - Whether semantic similarity was a factor.  
  - Any quality score influence. 

Institutions are encouraged to link OER_Phoenix to their own AI usage guidelines and academic integrity policies.
***

## Configuration and extensibility

OER_Phoenix is designed to be configurable and extensible without heavy forking.

### Harvesters

- New OAI‑PMH, REST, CSV, or MARCXML sources can be added via presets or manual configuration.  
- A template‑driven REST harvester allows many APIs to be configured declaratively through field mappings rather than new Python code. 

### Enrichment backends

Enrichment is implemented via a backend interface. You can:

- Use the default LLM‑based backend.  
- Enable a rules‑based backend that extracts keywords without external API calls.  
- Implement your own backend (e.g. institution’s in‑house NLP service) by conforming to the documented interface in `docs/enrichment.md`.

### Theming and branding

Institutions can customise:

- Site title and logo.  
- Primary colour palette.  
- Footer links and About text.

See `docs/theming.md` for details.

***

## Security, privacy, and data protection

OER_Phoenix primarily processes **metadata and URLs** for open educational resources, but AI‑related features and logging can still raise privacy and compliance questions.

Recommended practices:

- Do not ingest or store sensitive personal data in resource metadata or prompts.  
- If using external AI APIs, review their data retention policies and ensure you have appropriate contracts/DPAs.  
- Restrict access to staff‑only tools (e.g. RAG test interface, raw logs) to authenticated, authorised users.  
- Enable HTTPS, strong admin passwords, and regular updates of dependencies. 

See `docs/security.md` for more detailed guidance and checklist items.

***

## Contributing

Contributions are welcome from libraries, developers, educators, and students.

Ways to contribute:

- Bug reports and feature requests via GitHub Issues.  
- Pull requests for:
  - New harvester presets.  
  - UI/UX improvements.  
  - Documentation improvements, including translations.  
- Sharing deployment experiences and institutional configurations.

Please read `CONTRIBUTING.md` for:

- Code style and linting rules.  
- Branching strategy.  
- How to run the test suite and CI locally.

***

## Roadmap

Short‑term priorities (next major iteration): 

- Staff dashboard with streamlined workflows.  
- Pipeline visibility (harvested/enriched/embedded/scored flags and filters).  
- Clear separation and labelling of AI‑generated vs source metadata.  
- “Why this result?” explanations in search.  
- Pluggable enrichment backends and improved documentation.  
- Minimal vs full deployment profiles.

Longer‑term directions:

- More robust analytics on OER usage and coverage.  
- Additional integrations (LMS, institutional repositories).  
- Community‑maintained presets for a wider set of OER providers.

***


The project:

- Started as an internal R&D initiative and is now evolving into a reusable platform for other institutions.  
- Is openly licensed to encourage collaboration, scrutiny, and reuse.  
- Welcomes partnerships with libraries, teaching teams, and researchers interested in AI‑supported knowledge curation.

For institutional enquiries or collaboration proposals, please see the contact details in `docs/contact.md` or use the GitHub Discussions board.

***

## License

OER_Phoenix is released under the **MIT License**. See `LICENSE` for full terms. 

***

If you want, next step can be to generate matching `docs/architecture.md`, `docs/enrichment.md`, and `docs/security.md` skeletons so your AI coding workflow always has authoritative references to draw on.
