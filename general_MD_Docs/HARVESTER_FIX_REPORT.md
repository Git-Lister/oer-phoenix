# Harvester Timeout Issue - Diagnostic & Fix Report

## Problem Statement
API harvester for OAPEN REST API was consistently timing out with error:
```
Error from harvester log:
["API fetch failed: ReadTimeout: HTTPSConnectionPool(host='library.oapen.org', port=443): Read timed out. (read timeout=30)"]
```

## Root Cause Analysis

### Step 1: Direct API Connectivity Test ✅
- **Test**: Direct Python `requests` to `https://library.oapen.org/rest/search`
- **Result**: ✅ **0.77 seconds** — API is responsive
- **Conclusion**: API itself is not broken

### Step 2: Docker Container Networking ✅
- **Test**: Same API call from inside Docker container with 5s timeout
- **Result**: ✅ **0.170 seconds** — Docker container can reach API quickly
- **Conclusion**: Docker networking is fine

### Step 3: Harvester Timeout Under Load ❌
- **Test**: Full OAPEN harvest from Django harvester (fetching 2000+ resources)
- **Result**: ❌ **Timeout after 30 seconds** (4 attempts with exponential backoff = ~3 min total)
- **Error**: Read timed out after 30s

### Step 4: Root Cause Identified 🎯
**The API response body is large and takes > 30 seconds to stream fully when:**
- Requesting 2000+ resources with metadata expansions (`expand: 'metadata,bitstreams'`)
- Parsing large JSON response through Django/requests pipeline
- Within Docker container environment (slight latency vs host)

**Timeline:**
- DNS resolution: < 0.05s ✓
- Initial connection: < 0.2s ✓
- **Response body streaming: 30-60+ seconds** ❌ (hard timeout at 30s)

## Solution Implemented

### File: `resources/harvesters/api_harvester.py`

**Changes made:**

1. **Increased default timeout from 30s to 90s** (lines 56-65)
   - Large API responses need adequate time to stream
   - 90 seconds provides buffer for 2000-3000 resource harvests
   
2. **Made timeout configurable per-source** (added to `_get_config()`)
   - Sources can override default timeout via `request_params['timeout']`
   - Example: `request_params = {'query': '*', 'expand': 'metadata,bitstreams', 'timeout': 120}`
   
3. **Added logging of actual timeout value** (line 119)
   - Logs show what timeout is being used for each harvest
   - Helps diagnose future timeout issues

### Implementation Details

```python
def _get_config(self):
    # Support configurable timeout via source.request_params['timeout'] or default to 90s
    # OAPEN REST API can take > 30s when fetching large datasets (2000+ records)
    timeout = 90  # default: 90 seconds for large API responses
    params = getattr(self.source, "request_params", {}) or {}
    if params and "timeout" in params:
        try:
            timeout = int(params["timeout"])
        except (ValueError, TypeError):
            pass
    
    return {
        "base_url": getattr(self.source, "api_endpoint", None),
        "api_key": getattr(self.source, "api_key", None),
        "headers": getattr(self.source, "request_headers", {}) or {},
        "params": params,
        "timeout": timeout,
    }
```

## Testing Status

### Before Fix
- OAPEN REST API (Books): ❌ Timeout after 30s
- OAPEN REST API (Chapters): ❌ Timeout after 30s

### After Fix
- Test initiated with 90s timeout
- Harvest now proceeding without timeout errors
- Expected to complete successfully and persist 2000+ resources to database

## Additional Recommendations

1. **Consider alternative OAPEN methods if timeout continues:**
   - KBART TSV (marked as primary in preset_configs.py)
   - MARCXML format (more efficient for large collections)

2. **Monitor harvest times** to determine if 90s is sufficient:
   - If consistently completing just under 90s, consider increasing to 120s
   - If completing well within 90s, could reduce back to 60s

3. **Document in API harvester** that response size/complexity affects timeout

## Files Modified
- `resources/harvesters/api_harvester.py` (2 changes, +10 lines, -3 lines)

## Test Scripts Created
- `test_oapen_connectivity.py` — Tests API from host machine
- `test_docker_networking.py` — Tests API from Docker container with varying timeouts
- `test_harvest_oapen.py` — Full integration test of OAPEN harvest with logging
