# Per-Resource Detail Pages - Implementation Guide

## Overview

Implemented per-resource detail pages that provide rich metadata views with related resources and optional AI summaries. All features reuse existing infrastructure (embeddings, search engine) without introducing new indices or live LLM calls.

## Architecture

### Performance Design
- **1 DB fetch** (with `select_related("source")` to avoid N+1 queries)
- **1 vector search** (semantic search on resource content to find ~6 related items)
- **0 LLM calls** at request time (all summaries precomputed via Celery)

### Data Flow
```
User clicks resource title in search results
    ↓
Link points to: /resource/{pk}/
    ↓
resource_detail view:
  1. Fetch OERResource by PK
  2. Build "self-query" from resource's text
  3. Run semantic_search() to find related items
  4. Read precomputed ai_summary field (if exists)
  5. Render template with all data
    ↓
Template shows:
  - Full metadata (author, publisher, license, etc.)
  - AI summary card (if available)
  - Related resources sidebar with relevance scores
  - Action buttons (Open Resource, View at Source)
```

## Implementation Details

### 1. URL Routes (resources/urls.py)

Added two routes:
```python
path('resource/<int:pk>/', views.resource_detail, name='resource_detail'),
path('r/<int:pk>/', views.resource_shortlink, name='resource_shortlink'),
```

**Purpose:**
- `resource/{pk}/` — Primary detail page URL
- `r/{pk}/` — Short URL that redirects to full detail (useful for citations, exports, etc.)

### 2. View Functions (resources/views.py)

#### `resource_shortlink(request, pk)`
Simple redirect for short URLs:
```python
def resource_shortlink(request, pk):
    """Short URL redirect to full detail page (e.g., /r/123/ → /resource/123/)"""
    return redirect("resources:resource_detail", pk=pk, permanent=True)
```

#### `resource_detail(request, pk)`
Main detail page view with three steps:

**Step 1: Fetch Resource**
```python
resource = OERResource.objects.select_related("source").get(pk=pk)
```
- Uses `select_related` to avoid N+1 query for source data
- 404 handling with user feedback

**Step 2: Find Related Resources**
```python
base_text = (
    (resource.extracted_text or "")[:2000]
    or (resource.description or "")
    or resource.title
)
if base_text:
    engine = OERSearchEngine()
    related_results = engine.semantic_search(query=base_text, limit=6)
    related_results = [r for r in related_results if r.resource.id != resource.id][:5]
```
- Uses existing `OERSearchEngine` (no new code)
- Performs semantic search on resource's own content
- Filters out self
- Limits to 5 results

**Step 3: Pass Context to Template**
```python
context = {
    "resource": resource,
    "related_results": related_results,
    "ai_summary": getattr(resource, "ai_summary", None),
}
return render(request, "resources/resource_detail.html", context)
```

### 3. Template (templates/resources/resource_detail.html)

**Two-column layout:**

**Left Column (8/12 width on desktop):**
- Back link to search
- Gradient header with title, language, source badge, resource type
- Description section
- AI Summary card (if precomputed)
- Comprehensive metadata grid (author, publisher, date, subject, keywords, license, language, level, format, source)
- Action buttons (Open Resource, View at Source)
- Staff-only quality badge (for internal reference)

**Right Column (4/12 width on desktop):**
- Related resources sidebar
- Each related item shows:
  - Title (linked to its detail page)
  - Source badge
  - **AI match: X%** (using unified `relevance_pct`)
  - Description preview
  - "View details" link
- Empty state message if no related items found

**Responsive design:**
- Stacks to single column on mobile (<768px)
- Fixed-width buttons become full-width on mobile

### 4. Template Integration (templates/resources/search.html)

Updated search results to link to detail pages:

#### Classic Search Results
```html
<!-- Before -->
<h5 class="card-title mb-1">
  {{ r.resource.title }}
</h5>

<!-- After -->
<h5 class="card-title mb-1">
  <a href="{% url 'resources:resource_detail' r.resource.id %}" class="text-decoration-none">
    {{ r.resource.title }}
  </a>
</h5>
```

#### RAG Cited Resources
```html
<!-- Before -->
<a href="{{ resource.url }}" target="_blank" class="text-decoration-none">
  <strong>[R{{ resource.id }}]</strong> {{ resource.title }}
</a>

<!-- After -->
<a href="{% url 'resources:resource_detail' resource.id %}" class="text-decoration-none">
  <strong>[R{{ resource.id }}]</strong> {{ resource.title }}
</a>
```

**Note:** Kept external "Visit" buttons for direct resource access

## User Experience Flow

### Scenario 1: Browse from AI Search
```
1. User searches "machine learning basics"
2. Results show 10 items with titles as links + relevance %
3. User clicks "Understanding ML Algorithms" title
4. Navigates to /resource/42/
5. Sees full metadata, AI summary (if available), 5 related resources
6. Can click "Open Resource" to visit external URL
7. Or click related resource title to explore similar content
```

### Scenario 2: Browse from RAG Answer
```
1. User asks "What are common ML algorithms?"
2. RAG generates answer with cited resources [R42] [R89] [R156]
3. User clicks [R42] "Machine Learning Basics" title
4. Navigates to /resource/42/
5. Explores related resources from sidebar
6. Clicks "Related resource" → navigates to /resource/103/
7. Creates exploration chain without leaving the platform
```

### Scenario 3: Share Resource Link
```
1. User finds resource 42 useful
2. Copies URL: /r/42/
3. Shares with colleague
4. Colleague visits /r/42/
5. Redirects to /resource/42/ (permanent redirect)
6. Same rich detail page loads
```

## Optional: AI Summary Pipeline (Future Enhancement)

The plan suggests adding precomputed AI summaries. Here's how to implement this later:

### 1. Add Database Field
```python
# In resources/models.py OERResource class
ai_summary = models.TextField(blank=True, null=True, help_text="Precomputed AI summary of resource content")

# Then run migration:
# python manage.py makemigrations
# python manage.py migrate
```

### 2. Add Celery Task
```python
# In resources/tasks.py
@shared_task
def generate_resource_summary(resource_id):
    """Generate AI summary for a single resource."""
    try:
        resource = OERResource.objects.get(id=resource_id)
        
        # Build concise prompt
        prompt = f"""
        Provide a brief (2-3 sentence) summary of this educational resource:
        
        Title: {resource.title}
        Description: {resource.description}
        Subject: {resource.subject}
        
        Summary:
        """
        
        client = get_llm_client()
        summary = client.invoke(prompt)
        
        resource.ai_summary = summary.strip()
        resource.save()
        
        logger.info(f"Generated summary for resource {resource_id}")
    except Exception as e:
        logger.error(f"Error generating summary for {resource_id}: {e}")
```

### 3. Backfill Existing Resources
```python
# In resources/management/commands/backfill_summaries.py
from django.core.management.base import BaseCommand
from resources.models import OERResource
from resources.tasks import generate_resource_summary

class Command(BaseCommand):
    help = "Backfill AI summaries for resources where ai_summary IS NULL"
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1000,
                          help='Maximum number of resources to process')
    
    def handle(self, *args, **options):
        limit = options['limit']
        
        # Find resources without summaries
        missing = OERResource.objects.filter(
            ai_summary__isnull=True,
            is_active=True
        )[:limit]
        
        self.stdout.write(f"Enqueueing {missing.count()} summary tasks...")
        
        for resource in missing:
            generate_resource_summary.delay(resource.id)
            self.stdout.write(f"  → Resource {resource.id}")
        
        self.stdout.write(self.style.SUCCESS("Done"))
```

Usage:
```bash
# Process 100 resources
docker compose exec web python manage.py backfill_summaries --limit 100

# Or all missing summaries
docker compose exec web python manage.py backfill_summaries --limit 999999
```

### 4. View Behavior (Already Implemented)
The `resource_detail` view already checks for and displays `ai_summary`:
```python
ai_summary = getattr(resource, "ai_summary", None)
# Template displays if not None
```

No changes needed! Just run backfill command when field is added.

## Performance Characteristics

### Database Queries
- **Page load**: 1 DB query (select_related avoids N+1)
- **Related items**: 1 vector search (via pgvector)
- **Total**: ~2 queries per request

### Response Time Estimates
- **Resource fetch**: <10ms (indexed by PK)
- **Vector search**: 50-150ms (depends on dataset size, pgvector indexing)
- **Template render**: 10-50ms
- **Total**: ~100-200ms typical

### Caching Opportunity (Future)
If detail pages become slow:
```python
@cache_page(60 * 5)  # Cache for 5 minutes
def resource_detail(request, pk):
    # ... implementation
```

## Testing Checklist

- [ ] Navigate to `/resource/1/` (valid resource)
- [ ] Verify title, description, metadata display
- [ ] Verify "Related resources" sidebar shows items
- [ ] Verify each related item has relevance % score
- [ ] Click related resource title → navigates to its detail page
- [ ] Click "Open Resource" button → opens external URL in new tab
- [ ] Click "View at Source" button (if available)
- [ ] Test `/r/1/` short URL → redirects to `/resource/1/`
- [ ] Navigate back from search results → "Back to Search" link works
- [ ] Test on mobile → layout responsive, buttons full-width
- [ ] Test with resource that has no description → handles gracefully
- [ ] Test with resource that has no related items → shows empty state
- [ ] Verify AI summary displays if precomputed (after backfill command)
- [ ] Verify staff-only quality badge appears for staff users

## Deployment Notes

### No Schema Changes Yet
- No database migrations required (ai_summary field is optional, can add later)
- All code uses existing fields and services
- Safe to deploy alongside current RAG implementation

### URLs Are Stable
- Both `/resource/{pk}/` and `/r/{pk}/` will remain stable URLs
- Can be shared externally, added to exports, included in emails
- `r/` URLs use permanent redirects for SEO

### Related to Existing Features
- Uses same `OERSearchEngine` as AI Search
- Uses same `relevance_pct` score as everywhere else
- No new dependencies or libraries
- No new configuration needed

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `resources/urls.py` | Added 2 URL routes | +4 |
| `resources/views.py` | Added `resource_shortlink()` and `resource_detail()` views | +60 |
| `templates/resources/search.html` | Updated 2 title links to point to detail pages | +6 |
| `templates/resources/resource_detail.html` | **NEW** - 290-line detail page template | +290 |

## Future Enhancements

1. **AI Summary Backfill** (see optional section above)
2. **Related Resources Filtering** - allow users to filter related items by type/subject
3. **Bookmarking** - save favorite resources
4. **Citation Export** - generate BibTeX, APA, Chicago citations
5. **Annotations** - users can highlight/annotate resource content
6. **Resource Rating** - user ratings + reviews
7. **Breadcrumb Navigation** - show search → result → detail path
8. **Print View** - CSS-optimized printable version
9. **Metadata Validation** - highlight missing fields for editors
10. **History/Changelog** - track metadata changes over time

---

**Implementation Date**: January 20, 2026  
**Status**: ✅ Complete and ready for testing  
**Performance**: Zero LLM calls, efficient vector search reuse  
**Next Step**: Optional AI summary field + backfill command
