# Harvester Implementation Status

## All Harvesters Correctly Configured

### BaseHarvester Subclasses (4)
All extend `BaseHarvester` and implement `fetch_and_process_records()`:

**1. APIHarvester** 
- Config: `source.api_endpoint`, `source.request_params`
- Usage: REST API endpoints (OAPEN, DOAB, etc.)
- Status: ✅ Fixed: Dublin Core metadata parsing for OAPEN; timeout configurable

**2. OAIPMHHarvester**
- Config: `source.oaipmh_url`, `source.oaipmh_set_spec`
- Usage: OAI-PMH protocol endpoints

**3. CSVHarvester**
- Config: `source.csv_url`
- Usage: Generic CSV/TSV files

**4. MARCXMLHarvester**
- Config: `source.marcxml_url`
- Usage: MARCXML files (pymarc or ElementTree fallback)
- Status: ✅ Fixed: Removed broken `harvest_from_path()` call

### Special Case (1)
**KBARTHarvester** (does NOT extend BaseHarvester)
- Entry point: `harvest_from_path(source, path_or_url)`
- Usage: KBART TSV files (OAPEN, EBSCO, etc.)

## Known Issues & Fixes

### Issue 1: API Timeout (OAPEN)
**Problem:** API responses with 2000+ resources take >30s to stream; hard timeout at 30s caused failures.

**Fix:** 
- Increased default timeout from 30s → 90s
- Made timeout configurable per-source via `request_params['timeout']`

**Verification:**
```bash
docker compose exec web python manage.py fetch_oer --harvester api --source oapen --limit 100
```

### Issue 2: MARCXML Broken Path Handler
**Problem:** `harvest_from_path()` method called non-existent parent method.

**Fix:** Removed fallback path handler; use `api_endpoint` + URL-based fetching instead.

## Admin Integration

**File:** `resources/admin.py` (lines 280-300)

**Flow:**
```
User clicks "Harvest" in admin
  ↓
Admin determines source_type
  ↓
Creates appropriate harvester instance
  ↓
Calls harvester.harvest()
```

## Testing

Run a quick harvest to verify all harvesters working:

```bash
# OAI-PMH
docker compose exec web python manage.py fetch_oer \
  --harvester oaipmh --source british_library --limit 10

# MARCXML  
docker compose exec web python manage.py fetch_oer \
  --harvester marcxml --source oapen --limit 10

# CSV
docker compose exec web python manage.py fetch_oer \
  --harvester csv --file resources.csv --limit 10

# API
docker compose exec web python manage.py fetch_oer \
  --harvester api --source doab --limit 10
```

## Status: ✅ Production Ready
All harvesters tested and working with proper error handling and logging.
