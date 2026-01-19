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
    
    print("=== Metadata array structure ===")
    if 'metadata' in record and isinstance(record['metadata'], list):
        metadata_list = record['metadata']
        print(f"Number of metadata entries: {len(metadata_list)}")
        
        # Print first 5 entries
        print("\n=== First 5 metadata entries ===")
        for i, entry in enumerate(metadata_list[:5]):
            print(f"\nEntry {i}:")
            print(f"  Type: {type(entry)}")
            if isinstance(entry, dict):
                print(f"  Keys: {list(entry.keys())}")
                print(f"  Content: {json.dumps(entry, indent=4, default=str)[:200]}")
