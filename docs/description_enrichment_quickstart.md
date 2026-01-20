# Description Enrichment Quick Start

## 5-Minute Test

### Step 1: Verify Celery Running
```powershell
docker compose ps | findstr celery
# Should show: oer_rebirth-celery-1 ... Up
```

### Step 2: Test Signal on New Resource

Open Django shell:
```powershell
docker compose exec web python manage.py shell
```

Create test resource:
```python
from resources.models import OERResource, OERSource

source = OERSource.objects.first()
r = OERResource.objects.create(
    source=source,
    title="Test Book from Springer",
    url="https://example.com",
    description="CC BY ebook published by Springer"  # Boilerplate
)

print(f"Created resource {r.id}")
print(f"Before: description_last_enriched_at = {r.description_last_enriched_at}")
exit()
```

### Step 3: Watch Celery

```powershell
docker compose logs -f celery | findstr enrich
```

Within 10-30 seconds, expect:
```
INFO: Enriched description for resource 123 (245 chars)
```

### Step 4: Verify Update

```powershell
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
r = OERResource.objects.get(id=123)
print(f"Updated at: {r.description_last_enriched_at}")
print(f"New description: {r.description[:150]}...")
exit()
```

Expected: `description_last_enriched_at` now has timestamp!

## Backfill Test Batch

### Preview (No Changes)
```powershell
docker compose exec web python manage.py backfill_descriptions_from_url `
  --preview `
  --limit 5
```

Output shows resources that would be enriched.

### Run Small Batch
```powershell
docker compose exec web python manage.py backfill_descriptions_from_url `
  --limit 10 `
  --batch-size 2
```

### Check Results
```powershell
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
enriched = OERResource.objects.filter(
    description_last_enriched_at__isnull=False
).count()
print(f"Total enriched: {enriched}")
exit()
```

## Full Backfill (Production)

```powershell
# Backfill entire KBART source (if boilerplate only)
docker compose exec web python manage.py backfill_descriptions_from_url `
  --source 2 `
  --batch-size 10 `
  --limit 500

# Monitor in separate terminal
docker compose logs -f celery | findstr enrich
```

## Troubleshooting

**Tasks not running:**
```powershell
# Check Celery alive
docker compose exec celery celery -A oer_rebirth ping

# Check broker connection
docker compose logs redis | findstr "error"
```

**Field not updating:**
```powershell
# Verify migration
docker compose exec web python manage.py showmigrations resources | findstr "0016"
```

**HTML extraction failing:**
```powershell
# Test manually
docker compose exec web python -c "
from resources.utils.description_utils import extract_description_from_html
import requests
html = requests.get('https://example.com').text
print(extract_description_from_html(html))
"
```
