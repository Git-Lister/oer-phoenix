# Description Enrichment - Quick Start Testing Guide

## ✅ What's Ready

- ✅ Boilerplate detection utility (`resources/utils/description_utils.py`)
- ✅ Celery task (`enrich_description_from_url` in `resources/tasks.py`)
- ✅ Signal handler (auto-triggers on new resources)
- ✅ Model field (`description_last_enriched_at`)
- ✅ Database migration (applied)
- ✅ Backfill command (ready to use)

---

## 5-Minute Test

### 1. Verify Celery is Running
```bash
docker compose ps | grep celery
# Should show: oer_rebirth-celery-1 ... Up
```

### 2. Test Signal on New Resource (Manual)

Inside Django shell:
```bash
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource, OERSource

# Get a source (or use any existing source)
source = OERSource.objects.first()

# Create test resource with boilerplate description
r = OERResource.objects.create(
    source=source,
    title="Test Book from Springer",
    url="https://example.com",
    description="CC BY ebook published by Springer"  # Boilerplate
)

print(f"Created resource {r.id}")
print(f"Before: description_last_enriched_at = {r.description_last_enriched_at}")

# Exit shell and check logs
exit()
```

### 3. Watch Celery Logs
```bash
docker compose logs -f celery | grep -i "enriched\|enrichment"
```

Within ~10-30 seconds, you should see:
```
INFO: Enriched description for resource 123 (245 chars)
```

### 4. Verify Field Updated
```bash
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
r = OERResource.objects.get(id=123)
print(f"description_last_enriched_at: {r.description_last_enriched_at}")
print(f"New description: {r.description[:100]}...")
exit()
```

Expected: Field is now populated with timestamp!

---

## Backfill a Test Batch

### 1. Preview (Safe, No Changes)
```bash
docker compose exec web python manage.py backfill_descriptions_from_url --dry-run
```

Output shows how many resources would be processed.

### 2. Backfill Specific Source (e.g., KBART)

First, find KBART source ID:
```bash
docker compose exec web python manage.py shell
```

```python
from resources.models import OERSource
sources = OERSource.objects.filter(source_type__icontains='kbart')
for s in sources:
    print(f"ID: {s.id}, Name: {s.display_name}, Type: {s.source_type}")
exit()
```

Then backfill:
```bash
# Preview first
docker compose exec web python manage.py backfill_descriptions_from_url \
  --source-id 5 --limit 10 --dry-run

# Actually backfill
docker compose exec web python manage.py backfill_descriptions_from_url \
  --source-id 5 --limit 10
```

### 3. Monitor Progress
```bash
docker compose logs -f celery | grep "Enriched description"
```

---

## Verify Installation

All of these should work without errors:

```bash
# Import the utility module
docker compose exec web python -c "from resources.utils.description_utils import is_boilerplate_description; print('✓ Utility module loaded')"

# Verify task exists
docker compose exec web python -c "from resources.tasks import enrich_description_from_url; print('✓ Celery task loaded')"

# Check model field
docker compose exec web python manage.py shell -c "from resources.models import OERResource; print('✓ Model loaded'); print(OERResource._meta.get_field('description_last_enriched_at'))"

# Check migration applied
docker compose exec web python manage.py showmigrations resources | grep 0016
# Should show: [X] 0016_oerresource_description_last_enriched_at
```

---

## Common Issues & Fixes

### Issue: Task Not Running

```bash
# Check Celery is actually running
docker compose ps celery

# If not up, restart
docker compose restart celery

# Verify task registered
docker compose exec web celery -A oer_rebirth inspect registered | grep enrich_description
```

### Issue: Signal Not Triggering

1. Check if resource has a URL
2. Check if description is actually boilerplate:
   ```bash
   docker compose exec web python manage.py shell
   ```
   ```python
   from resources.utils.description_utils import is_boilerplate_description
   text = "CC BY ebook published by Springer"
   print(is_boilerplate_description(text))  # Should print True
   ```

### Issue: Migration Not Applied

```bash
# Check status
docker compose exec web python manage.py showmigrations resources | tail -5

# If 0016 shows [X], it's applied
# If it shows [ ], apply it
docker compose exec web python manage.py migrate resources
```

---

## Next Steps

After testing:

1. **Expand Boilerplate Patterns**
   - Run backfill with `--dry-run` on real KBART sources
   - Note common patterns
   - Add to `BOILERPLATE_SNIPPETS` in `resources/utils/description_utils.py`

2. **Run Full Backfill** (if satisfied with testing)
   ```bash
   docker compose exec web python manage.py backfill_descriptions_from_url \
     --source-id <KBART_ID> \
     --batch-size 50
   ```

3. **Monitor in Production**
   - Watch Celery logs
   - Check `description_last_enriched_at` is populating
   - Monitor success rates

---

## Files to Know

| File | Purpose |
|------|---------|
| `resources/utils/description_utils.py` | Boilerplate detection + HTML extraction |
| `resources/tasks.py` | Celery task (search for `enrich_description_from_url`) |
| `resources/signals.py` | Signal handler that triggers task |
| `resources/models.py` | OERResource model with new field |
| `resources/management/commands/backfill_descriptions_from_url.py` | CLI for batch processing |

---

## Success Indicators

✅ You're good when you see:

1. New resources automatically get enriched (signal triggers)
2. `description_last_enriched_at` populates with timestamp
3. Descriptions improve from boilerplate → real metadata
4. Backfill command processes batches without errors
5. Celery logs show consistent success messages

**Estimated Time to Test:** 10-15 minutes  
**Production Ready:** Once satisfied with test results
