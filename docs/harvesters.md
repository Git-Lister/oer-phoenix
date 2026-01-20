# Harvesters & Architecture

## Harvester Overview

OER Rebirth supports four harvester types for ingesting resources from external sources. Each harvester inherits from `BaseHarvester` and implements source-specific parsing logic.

### Harvester Types

#### 1. OAI-PMH Harvester
**File:** `resources/harvesters/oaipmh_harvester.py`

Standard protocol for metadata harvesting. Supports incremental harvests via resumption tokens.

**Usage:**
```bash
python manage.py fetch_oer --harvester oaipmh --source british_library
```

**Features:**
- Pagination via resumption tokens
- Incremental harvests (since date filtering)
- Metadata format negotiation
- Error recovery and retry

#### 2. MARCXML Harvester
**File:** `resources/harvesters/marcxml_harvester.py`

Parses MARCXML records (primarily library catalogs). Maps MARC fields to OERResource attributes.

**Usage:**
```bash
python manage.py fetch_oer --harvester marcxml --source oapen --file records.xml
```

**Features:**
- MARC field mapping (245 → title, 520 → description, etc.)
- Leader/directory parsing
- Subfield extraction

#### 3. CSV Harvester
**File:** `resources/harvesters/csv_harvester.py`

Flexible CSV import with configurable column mapping.

**Usage:**
```bash
python manage.py fetch_oer --harvester csv --file resources.csv --delimiter ','
```

**Features:**
- Custom column mapping
- Type inference
- Error reporting with row numbers

#### 4. REST API Harvester
**File:** `resources/harvesters/api_harvester.py`

Generic REST API client with pagination support.

**Usage:**
```bash
python manage.py fetch_oer --harvester api --source doab --limit 500
```

**Features:**
- Pagination (offset/limit or cursor-based)
- HTTP authentication (Basic, Bearer token)
- Response filtering and transformation

### Base Harvester Class

**File:** `resources/harvesters/base_harvester.py`

All harvesters inherit from `BaseHarvester` and implement:

```python
class BaseHarvester(ABC):
    def fetch(self) -> HarvestResult:
        """Main harvest method. Returns count, errors, warnings."""
    
    def parse_record(self, raw_record) -> dict:
        """Transform external record to OERResource fields."""
    
    def transform_to_resource_dict(self, parsed) -> dict:
        """Normalize parsed data to model fields."""
```

### Configuration

**File:** `resources/harvesters/preset_configs.py`

Pre-configured source profiles for quick harvesting.

**Example:**
```python
PRESET_CONFIGS = {
    'doab': {
        'harvester_type': 'api',
        'api_endpoint': 'https://directory.doab.org/api/v1/search',
        'pagination': {'type': 'offset', 'param': 'offset'},
    },
    'oapen': {
        'harvester_type': 'marcxml',
        'api_endpoint': 'https://oapen.org/api/oai',
    },
}
```

Add new sources here to make them available via `fetch_oer --source name`.

### Utilities

**File:** `resources/harvesters/utils.py`

Helper functions used across harvesters:
- `normalize_url()` – Parse and validate URLs
- `clean_text()` – Strip whitespace, normalize encoding
- `parse_date()` – Handle multiple date formats
- `map_license()` – Normalize license strings to standard values

---

## System Architecture

### Component Diagram

```
External Sources
    ↓ (OAI-PMH, MARCXML, CSV, API)
    ↓
Harvesters (Abstract classes + implementations)
    ↓ parse_record() → dict
    ↓
OERResource.objects.create/update()
    ↓ Signal: post_save
    ├─ Signal A: Enrich description (if boilerplate)
    │           └─ Celery task: enrich_description_from_url()
    │
    ├─ Signal B: Generate embedding (if enabled)
    │           └─ Celery task: generate_resource_embedding()
    │
    └─ Signal C: Index for search
                 └─ Celery task: index_resource_in_search()
    ↓
PostgreSQL + pgvector
    ├─ OERResource table + rows
    ├─ Vector embeddings column
    └─ Search indices
    ↓
REST API endpoints
    ├─ GET /api/search/ (hybrid)
    ├─ POST /api/rag-answer/
    └─ GET /admin/ (Django admin)
    ↓
Frontend
    ├─ Dashboard (query AI box)
    ├─ Search interface (filters + results)
    └─ Admin resource list
```

### Data Model

**OERResource** – Individual learning materials
- `id`, `source` (FK), `title`, `url`, `description`
- `creator`, `date_published`, `date_first_published` (new)
- `language`, `license`, `format`, `level`
- `keywords`, `coverage_notes`
- `content_embedding` (VectorField, pgvector)
- `overall_quality_score`
- `ai_subjects`, `primary_subject` (enriched)
- `description_last_enriched_at` (timestamp)
- `created_at`, `updated_at`

**OERSource** – Harvest sources
- `id`, `name`, `display_name`
- `source_type` (OAI-PMH, MARCXML, CSV, API)
- `api_endpoint`, `oai_base_url`, `marcxml_url`
- `field_mapping` (JSON)
- `schedule` (cron pattern)
- `is_active`

**HarvestJob** – Track harvest executions
- `id`, `source` (FK), `status`
- `resources_created`, `resources_updated`, `errors_count`
- `started_at`, `completed_at`
- `error_log` (text)

### Celery Task Flow

```
Harvest complete
    ↓
Signal fires for each new/updated resource
    ↓ [Multiple tasks queued]
    ├─ enrich_description_from_url(resource_id)
    │  ├─ HTTP GET resource.url
    │  ├─ extract_description_from_html()
    │  ├─ Update description if improved
    │  └─ Log result
    │
    ├─ generate_resource_embedding(resource_id)
    │  ├─ Load embedding model
    │  ├─ Embed title + description
    │  ├─ Store in pgvector column
    │  └─ Update embedding_generated_at
    │
    └─ index_resource_in_search(resource_id)
       ├─ Update Qdrant index (if enabled)
       ├─ Update PostgreSQL FTS
       └─ Mark indexed_at
```

### Search Architecture

**Hybrid Search Pipeline:**

```
User query
    ↓
OERSearchEngine.search(query, filters)
    ├─ [Keyword] PostgreSQL LIKE on title + description + keywords
    │            (with optional filters: source, license, date)
    │
    ├─ [Semantic] pgvector similarity search
    │             (embed query, find nearest neighbors)
    │
    └─ Merge + Normalize scores
                ↓
Return SearchResult[]
    {
        title, url, description,
        score (0-100),
        match_type (keyword|semantic|both),
        source, creator, license
    }
```

### RAG Pipeline

```
User question in dashboard Query AI box
    ↓
POST /api/rag-answer/ { query: "..." }
    ↓
answer_with_rag(query)
    ├─ search_engine.search(query) → top_k results
    │
    ├─ Format search results as context
    │
    ├─ Call LLM:
    │  "Given these resources: [..], answer: [query]"
    │
    └─ Parse LLM response → answer text + citations
    ↓
Return JSON
    {
        answer: "...",
        citations: [
            { title: "...", url: "...", resource_id: "..." },
            ...
        ]
    }
    ↓
Dashboard renders markdown answer + citation links
```

---

## Deployment & Monitoring

### Docker Services

```yaml
web:           # Django app + Gunicorn
db:            # PostgreSQL with pgvector extension
redis:         # Celery message broker
celery:        # Async worker
beat:          # Scheduled tasks (optional)
qdrant:        # Vector DB (optional, if SEARCH_BACKEND=qdrant)
pgadmin:       # DB admin UI (optional)
```

### Health Checks

```bash
# Web app
curl http://localhost:8000/health/

# Redis
docker compose exec redis redis-cli ping

# PostgreSQL
docker compose exec db psql -U oer_user -c "SELECT 1;"

# Qdrant (if running)
curl http://localhost:6333/health
```

### Monitoring Queries

```bash
# Resource count
docker compose exec web python -c "
from resources.models import OERResource
print(f'Total resources: {OERResource.objects.count()}')
"

# Enrichment rate
docker compose exec web python -c "
from resources.models import OERResource
enriched = OERResource.objects.filter(
    description_last_enriched_at__isnull=False
).count()
total = OERResource.objects.count()
print(f'Enriched: {enriched}/{total} ({100*enriched/total:.1f}%)')
"

# Active Celery tasks
docker compose exec celery celery -A oer_rebirth inspect active
```

---

## Adding a New Harvester

1. Create `resources/harvesters/my_harvester.py`
2. Inherit from `BaseHarvester`
3. Implement `fetch()` and `parse_record()`
4. Add preset config to `preset_configs.py`
5. Register in `resources/harvesters/__init__.py`

Example:
```python
class MyHarvester(BaseHarvester):
    def fetch(self) -> HarvestResult:
        # Implement harvest logic
        pass
    
    def parse_record(self, raw_record) -> dict:
        # Transform external format to OERResource fields
        return {
            'title': ...,
            'url': ...,
            ...
        }
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Harvest fails on large batch | Reduce `--batch-size` or `--limit` |
| Celery tasks queued but not executing | Check Redis: `docker compose logs redis` |
| pgvector extension missing | `docker compose exec db psql -c "CREATE EXTENSION vector;"` |
| OAI-PMH harvest slow | Check rate-limiting from source; add `--sleep-seconds 2` |
| Description enrichment stuck | Check URL validity; review Celery logs |
