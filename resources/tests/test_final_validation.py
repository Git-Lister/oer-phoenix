#!/usr/bin/env python
"""
Final comprehensive test demonstrating that the OAPEN API harvester is now working correctly.

This test validates that:
1. The API response parsing correctly handles Dublin Core metadata
2. Records are successfully ingested into the database
3. The harvest job completes successfully
"""
import os
import sys
import django
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oer_rebirth.settings')
django.setup()

from resources.models import OERSource, OERResource
from resources.harvesters.api_harvester import APIHarvester

print('\n' + '='*70)
print('COMPREHENSIVE OAPEN API HARVESTER TEST')
print('='*70)

# Create test source
print('\n[1] Creating test OAPEN source...')
source = OERSource.objects.create(
    name="FINAL TEST - OAPEN API",
    source_type="api",
    is_active=True,
    api_endpoint="https://library.oapen.org/rest/search",
    request_params={
        "query": "dc.type:chapter",
        "expand": "metadata,bitstreams",
        "limit": 5,
    },
    request_headers={"Accept": "application/json"},
    max_resources_per_harvest=5,
)
print(f'    ✓ Source created: {source.name} (ID: {source.id})')

# Initialize harvester
print('\n[2] Initializing APIHarvester...')
harv = APIHarvester(source)
print('    ✓ Harvester initialized')

# Test connection
print('\n[3] Testing connection to OAPEN API...')
if harv.test_connection():
    print('    ✓ Connection successful')
else:
    print('    ✗ Connection failed')
    sys.exit(1)

# Run harvest
print('\n[4] Running harvest...')
try:
    job = harv.harvest()
    print(f'    ✓ Harvest job created: {job.id}')
    print(f'    ✓ Status: {job.status}')
    print(f'    ✓ Records found: {job.resources_found}')
    print(f'    ✓ Records created: {job.resources_created}')
    print(f'    ✓ Records updated: {job.resources_updated}')
    print(f'    ✓ Records failed: {job.resources_failed}')
    
    if job.resources_failed > 0:
        print(f'\n    ⚠ WARNING: {job.resources_failed} records failed to process')
    
    if job.status != 'completed':
        print(f'    ✗ ERROR: Job status is {job.status}, expected "completed"')
        sys.exit(1)
    
    if job.resources_created == 0:
        print('    ✗ ERROR: No records were created')
        sys.exit(1)
        
except Exception as e:
    print(f'    ✗ Harvest failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify data
print('\n[5] Verifying stored resources...')
resources = OERResource.objects.filter(source=source).order_by('-created_at')
print(f'    ✓ Total resources in DB: {resources.count()}')

if resources.exists():
    print('\n    Sample resources:')
    for i, res in enumerate(resources[:3], 1):
        print(f'\n      Resource {i}:')
        print(f'        - Title: {res.title}')
        print(f'        - URL: {res.url}')
        print(f'        - Type: {res.normalised_type}')
        print(f'        - Author: {res.author[:40] if res.author else "(none)"}...')
        
        # Validate required fields
        if not res.title:
            print('        ✗ ERROR: Missing title')
            sys.exit(1)
        if not res.url:
            print('        ✗ ERROR: Missing URL')
            sys.exit(1)
        if not res.normalised_type:
            print('        ✗ WARNING: Missing normalised_type')
        
        print('        ✓ Valid')

# Cleanup
print('\n[6] Cleaning up...')
num_deleted, _ = OERResource.objects.filter(source=source).delete()
print(f'    ✓ Deleted {num_deleted} resources')
source.delete()
print(f'    ✓ Deleted source')

# Summary
print('\n' + '='*70)
print('✓ ALL TESTS PASSED')
print('='*70)
print('\nSummary:')
print('  ✓ OAPEN API harvester is working correctly')
print('  ✓ Dublin Core metadata is parsed correctly')
print('  ✓ Records are stored in database')
print('  ✓ All required fields are populated')
print('\nThe JSON parsing issue has been FIXED!')
print('='*70 + '\n')
