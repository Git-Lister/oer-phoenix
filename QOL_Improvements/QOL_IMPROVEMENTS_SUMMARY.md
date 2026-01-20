# UX/QOL Improvements - Summary of Changes

**Date**: January 20, 2026  
**Focus**: UI refinement, terminology alignment, behavior fixes  
**Impact**: Zero breaking changes, all improvements are backward compatible

## Changes Implemented

### 1. Fixed "View Record" Behavior for Missing Links

**File**: `resources/templatetags/oer_filters.py`  
**Function**: `link_type_button()`

**Problem**:
- When resource had no external URL, the filter displayed a "View record" button
- This triggered a search by title, which was confusing
- Titles already link to internal detail pages

**Solution**:
```python
# BEFORE: Generated confusing search button
return mark_safe(
    f'<a href="/search/?query={title}" class="btn btn-sm btn-outline-secondary">'
    'View record</a>'
)

# AFTER: Shows neutral text
return mark_safe(
    '<span class="text-muted small">No external link available</span>'
)
```

**Effect**:
- Resources without external links now show: "No external link available" (gray text)
- No confusing redundant buttons
- Title links to detail page as the primary discovery path
- Only external resources show action buttons (PDF, Repository, etc.)

---

### 2. Renamed "AI Query" (Terminology)

**File**: `templates/resources/search.html`

**Changes**:
```html
<!-- BEFORE -->
<label class="btn btn-outline-primary" for="mode-ask">
  <i class="bi bi-chat-dots"></i> Ask a Question
</label>
<h2 class="mb-0">AI Search Results</h2>
<head><title>AI Search - OER Platform</title></head>

<!-- AFTER -->
<label class="btn btn-outline-primary" for="mode-ask">
  <i class="bi bi-chat-dots"></i> AI Query
</label>
<h2 class="mb-0">Search Results</h2>
<head><title>Find Open Resources - OER Platform</title></head>
```

**Reasoning**:
- "AI Query" is more concise and technically accurate
- Emphasizes that results come from one unified system
- "Search Results" works for both classic search and AI Query results
- Page title now emphasizes primary action (finding resources)

**URLs/Functions Unchanged**:
- `ai_search()` view still named the same
- `rag_mode` parameter still used
- `/api/rag-answer/` endpoint still named the same
- Only user-facing labels changed

---

### 3. Reworked "Why This Result?" Explanation

**Files**: 
- `templates/resources/search.html`
- `templates/resources/advanced_search.html`

**Problem**:
- Old explanation referenced internal scoring details (quality scores, final_score calculations)
- Suggested per-result AI rationales (expensive, implied future LLM calls)
- Mentioned "Quality: X%" which is no longer displayed

**Solution**:
```html
<!-- BEFORE (expensive, internal details) -->
Matched via Semantic Match.
AI confidence 72%
(semantic similarity between your query and this resource).
Quality score 3.05 on a 0–5 scale, based on metadata completeness
Final ranking score 1.45 combines these signals...

<!-- AFTER (static, user-friendly) -->
This result is ranked using AI-powered semantic similarity between 
your query and the resource's title and description. 
Higher AI relevance values (shown above) indicate a closer conceptual match. 
Resources from curated collections or with richer metadata may be ranked 
slightly higher. The system prioritizes both semantic alignment and resource quality.
```

**Benefits**:
- ✅ No LLM calls triggered per result
- ✅ Explains the system without internal jargon
- ✅ Consistent wording across all result pages
- ✅ Sets expectations ("conceptual match", not "exact keyword match")
- ✅ Positions metadata quality as ranking factor (future enhancement hint)

---

### 4. Added "Semantic Match" Tooltip

**Files**:
- `templates/resources/search.html`
- `templates/resources/advanced_search.html`

**Change**:
```html
<!-- BEFORE: No explanation -->
<span class="badge bg-primary">Semantic Match</span>

<!-- AFTER: Helpful tooltip -->
<span class="badge bg-primary"
      data-bs-toggle="tooltip"
      title="Semantic Match means the AI compared the meaning of 
             your query to the resource content, not just matching 
             exact keywords. Higher AI relevance indicates a closer 
             conceptual match.">
  Semantic Match
</span>
```

**UX Pattern**:
- Tooltip appears on hover (Bootstrap tooltip pattern, already used in UI)
- Educates users without cluttering the layout
- Consistent with other tooltips ("AI relevance", etc.)

---

### 5. Advanced Search Alignment

**File**: `templates/resources/advanced_search.html`

**Updates**:
1. **Title links** → Now link to `resource_detail` (not just plain text)
   - Consistent with main search behavior
   - Provides internal discovery path

2. **Removed Quality badges**
   - Old: Displayed "Quality: 61%" from `overall_quality_score`
   - New: Removed (quality is internal ranking signal only)
   - Staff-only quality badge on detail pages still available

3. **Updated "Why this result?"**
   - Replaced old scoring explanation with new static text
   - Same explanation as main search for consistency

4. **Added Semantic Match tooltip**
   - Same tooltip as main search

5. **Unified relevance score**
   - Now shows `relevance_pct` (0-100) when available
   - Consistent with main search

**Effect**:
- Advanced Search results now look and behave like main search results
- No confusing dual-badge layouts
- Consistent terminology and explanations

---

## Visual Changes

### Search Results Cards - Before

```
┌─────────────────────────────────┐
│ Title                  [English]│
│ [Source] [Semantic Match]       │
│ [Quality: 61%] [AI confidence: 67%]
│ Why this result?                │
│ └─ Matched via Semantic Match   │
│    AI confidence 72%            │
│    Quality score 3.05 / 5.0     │
│    Final ranking score: 1.45    │
└─────────────────────────────────┘
```

### Search Results Cards - After

```
┌──────────────────────────────────┐
│ Title (linked to detail page)    │
│ [Source] [Semantic Match ⓘ]      │
│ [AI relevance: 67%]              │
│ Why this result?                 │
│ └─ This result is ranked using  │
│    AI-powered semantic           │
│    similarity...                 │
└──────────────────────────────────┘
```

**Key Differences**:
- ✅ Single unified relevance score (not dual badges)
- ✅ Tooltips explain what badges mean (hover-friendly)
- ✅ Explanation is generic, doesn't suggest future LLM calls
- ✅ Title is clickable (discovery-friendly)

---

## Backward Compatibility

✅ **No Breaking Changes**:
- All URL routes unchanged
- All view function names unchanged
- All API endpoints unchanged
- All database fields unchanged
- Template logic still receives same data
- Filter functions still work the same

✅ **Safe to Deploy**:
- Purely UI/UX refinement
- Can be deployed independently
- Can be reverted if needed
- No migration required

---

## Testing Checklist

- [ ] Navigate to main search page
- [ ] Verify "AI Query" button label shows (not "Ask a Question")
- [ ] Verify "Search Results" heading shows (not "AI Search Results")
- [ ] Click on result title → navigates to detail page
- [ ] Hover over "Semantic Match" badge → tooltip appears
- [ ] Click "Why this result?" → shows new static explanation
- [ ] Test resource with no external URL → shows "No external link available"
- [ ] Test resource with PDF → shows "Download PDF" button (unchanged)
- [ ] Navigate to Advanced Search
- [ ] Verify same behavior as main search
- [ ] Verify titles link to detail pages
- [ ] Verify Quality badges removed from results
- [ ] Check on mobile → layout responsive
- [ ] Verify tooltips work on touch devices (Bootstrap handles this)

---

## Performance Impact

✅ **No Performance Degradation**:
- No additional database queries
- No new API calls
- No additional rendering overhead
- Tooltips are CSS-based (instant)
- Static text explanations (no LLM calls)

---

## Future Enhancements

### Option 1: Lazy "Why This Result?" Explanation
Add endpoint `/api/why-this-result/{result_id}/` that:
- Only called when user explicitly clicks "Why this result?"
- Uses lightweight prompt + cached data
- Generates one-sentence explanation (not full paragraph)
- Optional feature for later

### Option 2: Curated Source Badges
Display special badges for:
- MMU-Vetted OER
- Peer Reviewed Collections
- Full Text Available
- etc.

These could be incorporated into the "Why this result?" explanation without LLM calls.

### Option 3: Metadata Quality Indicators
In detail page sidebar, show:
- "Metadata completeness: 85%"
- "All core fields present: Title, Author, License, ..."
- "Pedagogy indicators: Yes/No"

---

## Files Modified

| File | Changes | Type |
|------|---------|------|
| `resources/templatetags/oer_filters.py` | Removed "View record" search fallback | Python |
| `templates/resources/search.html` | Terminology, tooltips, static explanation | Template |
| `templates/resources/advanced_search.html` | Title links, removed quality badges, aligned behavior | Template |

**Total Lines Changed**: ~50 (minimal, focused edits)

---

## Summary

All five QOL improvements have been implemented:

✅ **Fixed "View record" behavior** — Shows neutral text when no external link  
✅ **Renamed "AI Query"** — More concise, accurate terminology  
✅ **Reworked "Why this result?"** — Static, user-friendly, no LLM overhead  
✅ **Added Semantic Match tooltip** — Educates users, Bootstrap-styled  
✅ **Advanced Search alignment** — Consistent behavior with main search  

**Ready to test and deploy!** 🚀
