import requests
import json

url = "https://library.oapen.org/rest/search"
params = {
    "query": "dc.type:chapter",
    "expand": "metadata,bitstreams",
    "limit": 1
}

response = requests.get(url, params=params, timeout=30)
data = response.json()

if isinstance(data, list) and len(data) > 0:
    record = data[0]
    print("=== Top-level record keys ===")
    print(json.dumps({k: str(v)[:50] if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>" for k, v in record.items()}, indent=2, default=str))
    
    print("\n=== Metadata structure ===")
    if 'metadata' in record:
        metadata = record['metadata']
        print(f"Metadata type: {type(metadata)}")
        print(f"Metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'Not a dict'}")
        if isinstance(metadata, dict):
            print("\n=== Metadata content (first 1000 chars) ===")
            print(json.dumps(metadata, indent=2, default=str)[:1000])
