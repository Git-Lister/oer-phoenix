# Deployment Verification Checklist

## Overview

Complete pre-production verification guide for the OER Rebirth system covering all core components, database schema, Celery integration, and testing procedures.

## Code Integration Checklist

- ✅ **Boilerplate Detection Utility** (`resources/utils/description_utils.py`)
  - Functions: `is_boilerplate_description()`, `extract_description_from_html()`
  - Status: Syntax verified, no errors

- ✅ **Celery Task** (`resources/tasks.py`, line 201)
  - Function: `enrich_description_from_url()`
  - Status: Merged and integrated

- ✅ **Signal Handler** (`resources/signals.py`, line 44)
  - Function: `enqueue_description_enrichment()`
  - Status: Auto-triggers on new resources

- ✅ **Model Enhancement** (`resources/models.py`)
  - Field: `description_last_enriched_at`
  - Method: `has_meaningful_description()`
  - Status: Complete

- ✅ **Database Migration** (`resources/migrations/0016_*`)
  - Status: Applied

- ✅ **Backfill Command** (`resources/management/commands/backfill_descriptions_from_url.py`)
  - Status: Ready for production use

## System Status Verification

### Python & Imports
```powershell
# Verify all modules load without errors
docker compose exec web python -c "
from resources.utils.description_utils import is_boilerplate_description
from resources.tasks import enrich_description_from_url
print('✓ All imports successful')
"
```

### Database
```powershell
# Verify migration applied
docker compose exec web python manage.py showmigrations resources | findstr "0016"
# Should show: [X] 0016_oerresource_description_last_enriched_at
```

### Celery
```powershell
# Check Celery worker is running
docker compose ps | findstr celery

# Verify task is registered
docker compose exec celery celery -A oer_rebirth inspect active_queues
```

## Pre-Production Testing

### Phase 1: Component Verification (5 minutes)

**Test Boilerplate Detection:**
```powershell
docker compose exec web python -c "
from resources.utils.description_utils import is_boilerplate_description
assert is_boilerplate_description('CC BY ebook published by Springer') == True
assert is_boilerplate_description('A comprehensive guide to biology') == False
print('✓ Boilerplate detection works')
"
```

**Test HTML Extraction:**
```powershell
docker compose exec web python -c "
from resources.utils.description_utils import extract_description_from_html
html = '<meta name=\"description\" content=\"Test article about climate science\">'
assert 'climate science' in extract_description_from_html(html)
print('✓ HTML extraction works')
"
```

### Phase 2: Signal & Task Flow (10 minutes)

**Create Test Resource:**
```powershell
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource, OERSource

source = OERSource.objects.first()
r = OERResource.objects.create(
    source=source,
    title="Test Resource",
    url="https://example.com",
    description="CC BY ebook published by Springer"
)
print(f"Created resource {r.id}")
exit()
```

**Monitor Celery:**
```powershell
docker compose logs -f celery | findstr "enrich"
# Look for: "INFO: Enriched description for resource 123"
```

**Verify Field Update:**
```powershell
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
r = OERResource.objects.get(id=123)
print(f"Enriched at: {r.description_last_enriched_at}")
print(f"New description: {r.description[:100]}...")
exit()
```

### Phase 3: Backfill (Production-like test)

**Preview Backfill:**
```powershell
docker compose exec web python manage.py backfill_descriptions_from_url \
  --preview \
  --limit 5
# Shows resources that would be enriched, no changes
```

**Run Small Batch:**
```powershell
docker compose exec web python manage.py backfill_descriptions_from_url \
  --limit 10 \
  --batch-size 2
```

**Verify Results:**
```powershell
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
enriched = OERResource.objects.filter(
    description_last_enriched_at__isnull=False
).count()
print(f"Resources enriched: {enriched}")
exit()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Celery task not executing | Verify `docker compose ps` shows celery running; check `CELERY_BROKER_URL` in `.env` |
| Field not updating | Check migration applied: `docker compose exec web python manage.py showmigrations` |
| HTML extraction failing | Verify BeautifulSoup installed: `docker compose exec web pip list \| findstr beautifulsoup` |
| Import errors | Restart web container: `docker compose restart web` |

## Sign-Off

- ✅ All components deployed
- ✅ Migrations applied
- ✅ Tests passing
- ✅ Ready for production
