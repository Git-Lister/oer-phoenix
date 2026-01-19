#!/usr/bin/env python
"""Diagnose Docker networking issues."""
import socket
import time
import requests

print('='*70)
print('[DOCKER] Network Diagnostics')
print('='*70)

# DNS test
host = 'library.oapen.org'
print(f'\n[1] DNS Resolution Test for {host}')
try:
    start = time.time()
    ip = socket.gethostbyname(host)
    elapsed = time.time() - start
    print(f'[✓] Resolved to: {ip} (took {elapsed:.3f}s)')
except socket.gaierror as e:
    print(f'[✗] DNS failed: {e}')

# Connection test with various timeouts
print(f'\n[2] Request Test with different timeouts')
for timeout_val in [5, 10, 15, 30, 60]:
    try:
        start = time.time()
        resp = requests.get('https://library.oapen.org/rest/search', 
                           params={'query': '*', 'limit': 1}, 
                           timeout=timeout_val)
        elapsed = time.time() - start
        print(f'[✓] Timeout={timeout_val}s: Connected status {resp.status_code}, took {elapsed:.3f}s')
        break
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start
        print(f'[✗] Timeout={timeout_val}s: Failed after {elapsed:.3f}s')
    except Exception as e:
        print(f'[✗] Timeout={timeout_val}s: Error {type(e).__name__}: {str(e)[:50]}')
        break

print('\n' + '='*70)
