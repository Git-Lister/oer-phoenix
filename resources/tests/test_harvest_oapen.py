#!/usr/bin/env python
"""Test harvest for OAPEN API source."""
import os
import sys
import django
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oer_rebirth.settings')
django.setup()

from resources.models import OERSource
from resources.harvesters.api_harvester import APIHarvester

print('='*70)
print('[TEST] OAPEN REST API Harvest Test')
print('='*70, flush=True)

src = OERSource.objects.get(pk=67)
print(f'Source: {src.name} (API)')
print(f'Endpoint: {src.api_endpoint}')
print(f'Params: {src.request_params}')
print(f'Active: {src.is_active}')
print(f'Max resources: {src.max_resources_per_harvest}')
print(flush=True)

harv = APIHarvester(src)
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
    if job.error_message:
        print(f'  Error Message: {job.error_message}', flush=True)
    if job.log_messages:
        print(f'  Logs: {job.log_messages}', flush=True)
except Exception as e:
    print(f'[✗] Harvest failed: {type(e).__name__}: {e}', flush=True)
    import traceback
    traceback.print_exc()

print('='*70)
print('[DONE]', flush=True)
