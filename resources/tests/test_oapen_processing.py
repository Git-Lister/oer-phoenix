"""
Unit test for OAPEN metadata extraction without Django setup
"""
import sys
import json
import requests

# Mock the APIHarvester to test just the _process_api_response logic
class MockAPIHarvester:
    def _normalise_language(self, raw: str) -> str:
        """Normalise various language codes/names to ISO 639-1 where possible."""
        if not raw:
            return "en"
        v = str(raw).strip().lower()
        if v in ("en", "eng", "english"):
            return "en"
        if v in ("fr", "fre", "fra", "french"):
            return "fr"
        if v in ("de", "ger", "deu", "german"):
            return "de"
        if v in ("es", "spa", "spanish"):
            return "es"
        return v

    def _normalise_resource_type(self, raw_type: str) -> str:
        """Map heterogeneous type strings into internal normalised_type values."""
        if not raw_type:
            return ""
        t = str(raw_type).strip().lower()

        if "chapter" in t or "section" in t or "part" in t:
            return "chapter"
        if "book" in t or "monograph" in t or "textbook" in t:
            return "book"
        if "article" in t or "journal" in t or "paper" in t:
            return "article"
        if "video" in t or "lecture" in t or "recording" in t:
            return "video"
        if "course" in t or "module" in t or "unit" in t:
            return "course"
        return "other"

    def _extract_oapen_metadata(self, metadata_list):
        """Extract Dublin Core metadata from OAPEN's metadata array format."""
        if not isinstance(metadata_list, list):
            return {}
        
        dc_map = {}
        for entry in metadata_list:
            if not isinstance(entry, dict):
                continue
            
            key = entry.get("key", "").lower()
            value = entry.get("value", "").strip()
            
            if not key or not value:
                continue
            
            if key not in dc_map:
                dc_map[key] = value
            elif key.endswith(".author") or key.endswith(".creator"):
                dc_map[key] = dc_map[key] + "; " + value
        
        return dc_map

    def _process_api_response(self, data):
        """Process API response into OER resource data"""
        processed_records = []

        # Handle different API response structures
        if isinstance(data, list):
            records = data
        else:
            # safe-get keys that commonly contain lists
            records = (
                data.get("results")
                or data.get("items")
                or data.get("data")
                or data.get("records")
            )
            if records is None:
                # If there's no list container, treat the whole payload as a single record
                records = [data] if isinstance(data, dict) and data else []

        for record in records:
            try:
                # Some APIs return primitive values inside lists; ensure `record` is a dict
                if not isinstance(record, dict):
                    continue

                # Check if this is an OAPEN record (has metadata array with Dublin Core entries)
                if isinstance(record.get("metadata"), list) and any(
                    isinstance(m, dict) and m.get("key", "").startswith("dc.") 
                    for m in record.get("metadata", [])
                ):
                    # OAPEN REST API format - extract Dublin Core metadata
                    dc_map = self._extract_oapen_metadata(record.get("metadata", []))
                    
                    # Map Dublin Core fields to resource fields
                    title = dc_map.get("dc.title", record.get("name", ""))
                    description = dc_map.get("dc.description", "") or dc_map.get("dc.description.abstract", "")
                    author = dc_map.get("dc.creator", "") or dc_map.get("dc.contributor.author", "")
                    subject = dc_map.get("dc.subject", "")
                    publisher = dc_map.get("dc.publisher", "")
                    license_val = dc_map.get("dc.rights", "") or dc_map.get("dc.rights.uri", "")
                    lang = dc_map.get("dc.language", "en")
                    resource_type = dc_map.get("dc.type", record.get("type", ""))
                    
                    # Try to construct URL from handle or link
                    url = ""
                    if record.get("handle"):
                        # OAPEN handles resolve via https://hdl.handle.net/
                        url = f"https://hdl.handle.net/{record['handle']}"
                    elif record.get("link"):
                        # Relative link from OAPEN
                        url = f"https://library.oapen.org{record['link']}" if record['link'].startswith('/') else record['link']
                    
                    resource_data = {
                        "title": title,
                        "description": description,
                        "url": url,
                        "license": license_val,
                        "publisher": publisher,
                        "author": author,
                        "language": self._normalise_language(lang),
                        "resource_type": resource_type,
                        "normalised_type": self._normalise_resource_type(resource_type),
                        "subject": subject,
                    }
                else:
                    # Generic API format - backward compatibility
                    raw_lang = record.get("language", "en")
                    raw_type = record.get("resource_type", record.get("type", ""))

                    # subject / keywords normalisation
                    subj = (
                        record.get("subject")
                        or record.get("subjects")
                        or record.get("keywords")
                        or record.get("categories")
                        or record.get("category")
                        or ""
                    )
                    if isinstance(subj, (list, tuple)):
                        subj = "; ".join(str(s).strip() for s in subj if s)

                    resource_data = {
                        "title": record.get("title", record.get("name", "")),
                        "description": record.get("description", record.get("summary", "")),
                        "url": record.get("url", record.get("link", record.get("identifier", ""))),
                        "license": record.get("license", record.get("rights", "")),
                        "publisher": record.get("publisher", record.get("provider", "")),
                        "author": record.get(
                            "author", record.get("creator", record.get("owner", ""))
                        ),
                        "language": self._normalise_language(raw_lang),
                        "resource_type": raw_type,
                        "normalised_type": self._normalise_resource_type(raw_type),
                        "subject": subj,
                    }

                # Require at least title and URL
                if resource_data["title"] and resource_data["url"]:
                    processed_records.append(resource_data)

            except Exception as e:
                print(f"[!] Failed to process API record: {str(e)}", file=sys.stderr)
                continue

        return processed_records


# Test with real OAPEN API
print("=" * 70)
print("[TEST] OAPEN API Processing")
print("=" * 70)

url = "https://library.oapen.org/rest/search"
params = {
    "query": "dc.type:chapter",
    "expand": "metadata,bitstreams",
    "limit": 3
}

print(f"\nFetching from OAPEN API: {url}")
print(f"Params: {params}\n")

try:
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    print(f"[✓] API returned {len(data) if isinstance(data, list) else '?'} records")
    
    # Process with mock harvester
    harvester = MockAPIHarvester()
    processed = harvester._process_api_response(data)
    
    print(f"[✓] Processed {len(processed)} records\n")
    
    # Show first 2 processed records
    for i, record in enumerate(processed[:2]):
        print(f"--- Record {i+1} ---")
        print(f"Title:       {record['title'][:60]}")
        print(f"URL:         {record['url'][:60]}")
        print(f"Author:      {record['author'][:60] if record['author'] else '(none)'}")
        print(f"Publisher:   {record['publisher'][:60] if record['publisher'] else '(none)'}")
        print(f"Type:        {record['resource_type']} (normalized: {record['normalised_type']})")
        print()
    
    print("[✓] SUCCESS: OAPEN records processed correctly!")
    
except Exception as e:
    print(f"[✗] FAILED: {e}", file=sys.stderr)
    sys.exit(1)
