#!/usr/bin/env python
"""Test harvest for OAPEN API source with smaller dataset."""
import os
import sys
import django
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oer_rebirth.settings')
django.setup()

from resources.models import OERSource
from resources.harvesters.api_harvester import APIHarvester

print('='*70)
print('[TEST] OAPEN REST API Harvest Test (Small Dataset)')
print('='*70, flush=True)

# Create a test source with smaller limit
source = OERSource.objects.create(
    name="Test OAPEN API (Small)",
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

print(f'Source: {source.name} (API)')
print(f'Endpoint: {source.api_endpoint}')
print(f'Params: {source.request_params}')
print(f'Max resources: {source.max_resources_per_harvest}')
print(flush=True)

harv = APIHarvester(source)

print('[1] Testing connection...',flush=True)
try:
    if harv.test_connection():
        print('[✓] Connection successful', flush=True)
    else:
        print('[✗] Connection failed', flush=True)
except Exception as e:
    print(f'[✗] Connection test error: {e}', flush=True)

print(flush=True)
print('[2] Fetching records...',flush=True)
sys.stdout.flush()

try:
    job = harv.harvest()
    print(f'[✓] Harvest completed', flush=True)
    print(f'  Status: {job.status}', flush=True)
    print(f'  Found: {job.resources_found}', flush=True)
    print(f'  Created: {job.resources_created}', flush=True)
    print(f'  Updated: {job.resources_updated}', flush=True)
    print(f'  Failed: {job.resources_failed}', flush=True)
    
    # Show sample resources created
    if job.resources_created > 0:
        from resources.models import OERResource
        recent = OERResource.objects.filter(source=source).order_by('-created_at')[:3]
        print(f'\n  Sample resources:', flush=True)
        for res in recent:
            print(f'    - {res.title[:50]}', flush=True)
    
    print(f'\n[✓] SUCCESS', flush=True)
    
except Exception as e:
    print(f'[✗] Harvest failed: {e}', flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    source.delete()
