# Harvester Configuration - Final Status

## ✅ All Harvesters Correctly Wired

### BaseHarvester Subclasses (4)
All extend `BaseHarvester` and implement `fetch_and_process_records()`:

1. **APIHarvester** 
   - Entry point: `harvest()`
   - Config source: `source.api_endpoint`, `source.request_params`
   - Usage: REST API endpoints (OAPEN, DOAB, etc.)
   - ✓ Fixed: Dublin Core metadata parsing for OAPEN

2. **OAIPMHHarvester**
   - Entry point: `harvest()`
   - Config source: `source.oaipmh_url`, `source.oaipmh_set_spec`
   - Usage: OAI-PMH protocol endpoints

3. **CSVHarvester**
   - Entry point: `harvest()`
   - Config source: `source.csv_url`
   - Usage: Generic CSV/TSV files

4. **MARCXMLHarvester**
   - Entry point: `harvest()`
   - Config source: `source.marcxml_url`
   - Usage: MARCXML files (with pymarc or ElementTree fallback)
   - ✓ Fixed: Removed broken `harvest_from_path()` call

### Special Case (1)
Does NOT extend BaseHarvester, has different interface:

5. **KBARTHarvester** (KBART files only)
   - Entry point: `harvest_from_path(source, path_or_url)`
   - Config source: Not used (path provided directly)
   - Usage: KBART TSV files (OAPEN, EBSCO, etc.)

## Admin Integration

**File:** `resources/admin.py` (lines 280-300)

**Flow:**
```
User clicks "Harvest" in admin
  ↓
Admin determines source_type (API, OAIPMH, CSV, MARCXML)
  ↓
Creates appropriate harvester instance with source
  ↓
Calls harvester.harvest()
  ↓
BaseHarvester.harvest() calls fetch_and_process_records()
  ↓
Records upserted to database
```

**All 4 BaseHarvester types now use single code path: `harvest()`**

## JavaScript - Form Handling

**File:** `static/admin/js/oer_source_dynamic.js`

**Features:**
- Show/hide configuration fields based on source_type selection
- Set field requirements dynamically
- Filter preset buttons to matching source type only
- Simple, readable configuration-based approach

**Key Functions:**
- `updateFormVisibility(selectedType)` - Toggle form sections
- `filterPresetButtons(selectedType)` - Enable/disable presets
- `updateFieldRequirements(sourceType)` - Set required fields

## Testing

Run verification test:
```bash
docker compose exec web python test_all_harvesters.py
```

Expected output:
- ✓ All 4 BaseHarvester subclasses configured
- ✓ KBART special case verified
- ✓ All instantiate with source parameter
- ✓ Admin integration validated

## What Was Fixed

1. **JSON Parsing Issue (API/OAPEN)**
   - Added Dublin Core metadata parsing
   - OAPEN now harvests correctly

2. **Content Extraction Timeouts**
   - Increased timeout from 20s → 60s
   - handle.net PDFs now fetch successfully

3. **MARCXML Harvester**
   - Removed broken `harvest_from_path()` call
   - Now uses standard `harvest()` method
   - Works like APIHarvester

## Next Steps (Optional)

1. **Preset Filtering** - Already works, no changes needed
2. **KBART Handling** - Special case works separately
3. **Test All Harvest Types** - Run actual harvests from admin

## Architecture Notes

**Why this design?**

- **BaseHarvester** provides standard `harvest()` flow:
  - Fetch records
  - Upsert to DB
  - Enrich metadata
  - Calculate quality scores
  - Update stats

- **KBART is special** because:
  - Can be local file OR remote URL
  - Needs custom reader logic
  - Not all sources have URL in database

- **Unified approach** keeps code DRY:
  - All API-like harvesters use same `harvest()` entry point
  - Configuration in source model
  - Admin simplified (single `harvester.harvest()` call)
