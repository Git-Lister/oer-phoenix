import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Direct OAPEN API call to inspect response structure
url = "https://library.oapen.org/rest/search"
params = {
    "query": "*",
    "expand": "metadata,bitstreams",
    "limit": 2  # Just 2 records to inspect
}

logger.info(f"Fetching from {url} with params: {params}")

try:
    response = requests.get(url, params=params, timeout=30)
    logger.info(f"Status: {response.status_code}")
    logger.info(f"Content-Type: {response.headers.get('content-type')}")
    
    # Try to parse as JSON
    try:
        data = response.json()
        logger.info(f"Response is valid JSON, type: {type(data)}")
        
        if isinstance(data, list):
            logger.info(f"Response is a list with {len(data)} items")
            if data:
                first_record = data[0]
                logger.info(f"\n=== First Record Structure ===")
                logger.info(f"Type: {type(first_record)}")
                logger.info(f"Keys: {first_record.keys() if isinstance(first_record, dict) else 'Not a dict'}")
                logger.info(f"\n=== First Record (pretty printed) ===")
                logger.info(json.dumps(first_record, indent=2, default=str)[:1000])  # First 1000 chars
        else:
            logger.info(f"Response structure: {type(data)}")
            logger.info(f"Top-level keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response text preview: {response.text[:500]}")
        
except Exception as e:
    logger.error(f"Request failed: {e}")
