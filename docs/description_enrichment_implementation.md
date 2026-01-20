# Description Enrichment Implementation

## Overview

Complete async description enrichment pipeline designed to replace weak/boilerplate KBART descriptions. System automatically enriches resource descriptions by fetching and parsing HTML content from source URLs.

**Status:** ✅ **COMPLETE AND DEPLOYED**

## Architecture

### 1. Boilerplate Detection & Extraction

**File:** `resources/utils/description_utils.py`

#### `is_boilerplate_description(text: str | None) -> bool`
- Normalizes input (lowercasing, whitespace stripping)
- Checks against `BOILERPLATE_SNIPPETS` pattern list
- Returns `True` if: None, <20 chars, or matches known patterns

**Known boilerplate patterns:**
```python
BOILERPLATE_SNIPPETS = [
    "springer cc by",           # Springer ebooks
    "© 20",                     # Copyright notices
    "published by",             # Generic text
]
```

#### `extract_description_from_html(html_content: str) -> str | None`

Multi-strategy extraction with fallback chain:
1. `<meta name="description" content="...">`
2. `<meta property="og:description" content="...">`
3. First `<p>` tag >100 chars
4. Text blocks in `<div>` tags with class/id

Returns None if no suitable text found. Handles BeautifulSoup variations and null-checks robustly.

### 2. Model Enhancement

**File:** `resources/models.py`

```python
class OERResource(models.Model):
    description_last_enriched_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp of last automatic description enrichment"
    )
    
    def has_meaningful_description(self) -> bool:
        """Check if resource has a non-boilerplate description"""
        from resources.utils.description_utils import is_boilerplate_description
        return not is_boilerplate_description(self.description)
```

**Migration:** `0016_oerresource_description_last_enriched_at.py` ✅ Applied

### 3. Celery Task

**File:** `resources/tasks.py` (line 201)

```python
@shared_task(bind=True, max_retries=3)
def enrich_description_from_url(self, resource_id: int) -> dict:
    """
    Fetch resource URL, extract description, update if boilerplate.
    
    Returns: {
        'resource_id': int,
        'boilerplate_detected': bool,
        'new_description_chars': int | None,
        'error': str | None
    }
    """
```

**Logic:**
1. Fetch resource by ID
2. Verify URL exists
3. HTTP GET with timeout
4. Check current description is boilerplate
5. Extract new description from HTML
6. Update resource + set timestamp
7. Return result dict

**Error handling:**
- Retries 3x on network timeout
- Logs failures with resource ID
- Doesn't fail harvests on enrichment errors
- Graceful fallback if BeautifulSoup unavailable

### 4. Signal Handler

**File:** `resources/signals.py` (line 44)

```python
@receiver(post_save, sender=OERResource)
def enqueue_description_enrichment(sender, instance, created, **kwargs):
    """Auto-enqueue enrichment task for new resources with boilerplate descriptions"""
    if created and is_boilerplate_description(instance.description):
        enrich_description_from_url.apply_async(
            args=(instance.id,),
            countdown=5  # 5-second delay to avoid task queue spam
        )
```

**Behavior:**
- Triggers on POST_SAVE with `created=True`
- Only enqueues if description is boilerplate
- 5-second countdown prevents burst loads
- Silent on enrichment errors (doesn't block harvest)

### 5. Backfill Command

**File:** `resources/management/commands/backfill_descriptions_from_url.py`

```bash
python manage.py backfill_descriptions_from_url [OPTIONS]
```

**Options:**
- `--limit N` – Process max N resources (default: 100)
- `--batch-size N` – Enqueue N tasks per batch (default: 10)
- `--preview` – Show what would be enriched, no changes
- `--with-valid` – Include resources with non-boilerplate descriptions
- `--source SOURCE_ID` – Filter by source

**Example:**
```bash
# Preview enrichment for first 20 KBART resources
python manage.py backfill_descriptions_from_url --limit 20 --preview

# Enqueue 50 resources in batches of 5
python manage.py backfill_descriptions_from_url --limit 50 --batch-size 5
```

## Configuration

**Environment variables** (`.env`):

```bash
# Optional: Custom user agent for HTTP requests
DESCRIPTION_ENRICHMENT_USER_AGENT=MyBot/1.0

# Optional: Custom request timeout (default: 10 seconds)
DESCRIPTION_ENRICHMENT_TIMEOUT=15

# Optional: Enable/disable (default: enabled)
DESCRIPTION_ENRICHMENT_ENABLED=true
```

## Data Flow

```
New OERResource created
        ↓
post_save signal fires
        ↓
is_boilerplate_description() → TRUE?
        ↓
enqueue_description_enrichment() task
        ↓
Celery worker executes task
        ↓
HTTP GET resource URL
        ↓
extract_description_from_html() → new description
        ↓
Update OERResource.description + set timestamp
        ↓
Log success/failure
```

## Monitoring

### Check Task Queue Status
```bash
docker compose exec celery celery -A oer_rebirth inspect active
```

### View Enrichment Success Rate
```bash
docker compose exec web python manage.py shell
```

```python
from resources.models import OERResource
total = OERResource.objects.count()
enriched = OERResource.objects.filter(
    description_last_enriched_at__isnull=False
).count()
print(f"Enriched: {enriched}/{total} ({100*enriched/total:.1f}%)")
```

### Recent Enrichments
```python
from resources.models import OERResource
from datetime import timedelta
from django.utils import timezone

since = timezone.now() - timedelta(hours=1)
recent = OERResource.objects.filter(
    description_last_enriched_at__gte=since
).order_by('-description_last_enriched_at')
print(f"Last hour: {recent.count()} enriched")
for r in recent[:5]:
    print(f"  {r.title}: {r.description_last_enriched_at}")
```

## Testing

### Unit Tests
```bash
python manage.py test resources.tests.test_description_enrichment
```

### Manual Task Test
```bash
docker compose exec web python manage.py shell
```

```python
from resources.tasks import enrich_description_from_url
result = enrich_description_from_url(123)  # resource_id
print(result)
```

## Known Limitations

- **Rate limiting:** External websites may block rapid requests; Celery countdown mitigates this
- **Dynamic content:** Only fetches static HTML; JavaScript-rendered pages fail
- **Charset detection:** Relies on HTTP headers; some sites may encode incorrectly
- **Timeout:** 10-second default may be too short for slow servers (configurable)

## Troubleshooting

| Issue | Check |
|-------|-------|
| Tasks not executing | `docker compose ps \| findstr celery` running? |
| All descriptions still boilerplate | Verify migration: `showmigrations resources` |
| Timeout errors | Increase `DESCRIPTION_ENRICHMENT_TIMEOUT` in .env |
| HTML extraction returning None | Check website structure; may need custom parser |

## Future Improvements

- Language detection and auto-translate descriptions
- Category inference from HTML structure
- Author/contributor extraction
- License detection from page headers
