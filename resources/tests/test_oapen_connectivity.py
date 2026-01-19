#!/usr/bin/env python
"""Test OAPEN API connectivity and response parsing."""
import requests
import time
import json

def test_oapen_api():
    url = 'https://library.oapen.org/rest/search'
    params = {'query': '*', 'expand': 'metadata,bitstreams', 'limit': 1}

    print('=' * 70)
    print('Testing OAPEN REST API Connectivity')
    print('=' * 70)
    print(f'URL: {url}')
    print(f'Params: {params}')
    print()

    start = time.time()
    try:
        print('[1] Initiating request with 30s timeout...')
        resp = requests.get(url, params=params, timeout=30, verify=True)
        elapsed = time.time() - start
        
        print(f'[✓] Status: {resp.status_code}')
        print(f'[✓] Response time: {elapsed:.2f}s')
        print(f'[✓] Content-Type: {resp.headers.get("content-type", "N/A")}')
        print(f'[✓] Response size: {len(resp.content)} bytes')
        print()
        
        print('[2] Validating JSON...')
        try:
            data = resp.json()
            print(f'[✓] Valid JSON: Yes')
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f'[✓] Top-level keys: {keys[:5]}')
                
                # Check for common container keys
                for container in ['results', 'items', 'data', 'records']:
                    if container in data:
                        print(f'[✓] Found container key: "{container}" with {len(data[container])} items')
                        if data[container]:
                            first = data[container][0]
                            print(f'[✓] First item keys: {list(first.keys())[:5]}')
                        break
        except json.JSONDecodeError as e:
            print(f'[✗] Valid JSON: No - {e}')
        
        print()
        print('[✓] Connectivity test PASSED')
        
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start
        print(f'[✗] ReadTimeout after {elapsed:.2f}s')
        print(f'[!] Error: {e}')
        
    except requests.exceptions.ConnectionError as e:
        print(f'[✗] Connection Error: {e}')
        
    except Exception as e:
        print(f'[✗] Unexpected Error: {type(e).__name__}: {e}')

if __name__ == '__main__':
    test_oapen_api()
