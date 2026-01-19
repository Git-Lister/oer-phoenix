#!/usr/bin/env python
"""Test OAPEN API with expand parameters and measure response time."""
import requests
import time

print('=' * 70)
print('[DIAG] OAPEN API Response Time with expand parameters')
print('=' * 70)

url = 'https://library.oapen.org/rest/search'
params = {'query': '*', 'expand': 'metadata,bitstreams', 'limit': 10}

print(f'\nURL: {url}')
print(f'Params: {params}')
print()

for timeout_val in [30, 60, 90, 120, 150, 180, 240, 300]:
    print(f'[Testing with timeout={timeout_val}s...]', end='', flush=True)
    try:
        start = time.time()
        resp = requests.get(url, params=params, timeout=timeout_val)
        elapsed = time.time() - start
        size_mb = len(resp.content) / (1024 * 1024)
        print(f' ✓ Status: {resp.status_code}, Time: {elapsed:.2f}s, Size: {size_mb:.2f}MB')
        
        # Try to parse JSON
        try:
            data = resp.json()
            items = data.get('_embedded', {}).get('items', [])
            print(f'    Found {len(items)} items in response')
        except:
            print(f'    Could not parse JSON')
        
        break  # Success, no need to continue
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start
        print(f' ✗ Timeout after {elapsed:.2f}s')
    except Exception as e:
        print(f' ✗ {type(e).__name__}: {str(e)[:50]}')

print()
print('=' * 70)
