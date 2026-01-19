#!/usr/bin/env python
"""Diagnose OAPEN API response format."""
import requests
import json

print('=' * 70)
print('[DIAG] OAPEN API Response Format Diagnosis')
print('=' * 70)

url = 'https://library.oapen.org/rest/search'
params = {'query': '*', 'expand': 'metadata,bitstreams', 'limit': 1}

print(f'\nURL: {url}')
print(f'Params: {params}')
print()

try:
    print('[1] Fetching response...')
    resp = requests.get(url, params=params, timeout=30)
    print(f'[✓] Status: {resp.status_code}')
    print(f'[✓] Content-Type: {resp.headers.get("content-type", "N/A")}')
    print(f'[✓] Response size: {len(resp.content)} bytes')
    print(f'[✓] Response text size: {len(resp.text)} chars')
    
    print('\n[2] Response first 500 chars:')
    print('-' * 70)
    print(resp.text[:500])
    print('-' * 70)
    
    print('\n[3] Attempting JSON parse...')
    try:
        data = resp.json()
        print(f'[✓] Valid JSON!')
        print(f'[✓] Type: {type(data).__name__}')
        if isinstance(data, dict):
            print(f'[✓] Top-level keys: {list(data.keys())}')
            if '_embedded' in data:
                items = data['_embedded'].get('items', [])
                print(f'[✓] Found {len(items)} items')
                if items:
                    print(f'[✓] First item keys: {list(items[0].keys())[:5]}')
    except json.JSONDecodeError as e:
        print(f'[✗] JSON Parse Error: {e}')
        print(f'[✗] Error at line {e.lineno}, col {e.colno}: {e.msg}')
        
except Exception as e:
    print(f'[✗] Error: {type(e).__name__}: {e}')

print()
print('=' * 70)
