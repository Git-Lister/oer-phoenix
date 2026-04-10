# resources/services/talis.py

import base64
import csv
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TextIO

import requests

logger = logging.getLogger(__name__)

TALIS_API_URL = "https://rl.talis.com/3/"

# ========== DATACLASSES (must be before TalisClient) ==========
@dataclass
class TalisItem:
    title: str = ""
    position: Optional[int] = None
    section: Optional[str] = None
    importance: Optional[str] = None
    item_type: Optional[str] = None
    authors: Optional[str] = None
    isbn: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[str] = None
    language: Optional[str] = None
    normalised_type: Optional[str] = None


@dataclass
class TalisList:
    identifier: str
    title: Optional[str]
    module_code: Optional[str]
    academic_year: Optional[str]
    source_type: str        # "csv" or "api"
    items: List[TalisItem] = field(default_factory=list)
    raw_payload_ref: Optional[str] = None


# ========== CLIENT ==========
class TalisClient:
    def __init__(self):
        self.tenant = os.getenv("TALIS_TENANT")
        self.client_id = os.getenv("TALIS_CLIENT_ID")
        self.client_secret = os.getenv("TALIS_CLIENT_SECRET")
        self.access_token = None

    def authenticate(self):
        """Authenticate with Talis API using OAuth2 Client Credentials Grant."""
        token_url = "https://users.talis.com/oauth/tokens"

        # Prepare the Basic Auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        auth_header = f"Basic {encoded_credentials}"

        # Set the correct headers for the token request
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # The request body for a client credentials grant
        data = {
            "grant_type": "client_credentials",
            "scope": "https://rl.talis.com/3/",
        }

        try:
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.info("Successfully authenticated with Talis API.")
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Talis authentication failed: {e}")
            if e.response is not None:
                logger.error(f"Response body: {e.response.text}")
            raise ConnectionError(f"Failed to authenticate with Talis: {e}")

    def _headers(self):
        if not self.access_token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/vnd.api+json",
        }

    def create_reading_list(self, title, description, resources):
        headers = self._headers()
        list_data = {
            "data": {
                "type": "lists",
                "attributes": {
                    "title": title,
                    "description": description,
                    "visibility": "PUBLIC",
                },
            }
        }
        list_url = f"{TALIS_API_URL}{self.tenant}/lists"
        list_response = requests.post(list_url, json=list_data, headers=headers)
        list_response.raise_for_status()
        list_id = list_response.json()["data"]["id"]

        items_url = f"{TALIS_API_URL}{self.tenant}/lists/{list_id}/items"
        for resource in resources:
            item_data = {
                "data": {
                    "type": "items",
                    "attributes": {
                        "uri": resource.url,
                        "meta": {
                            "title": resource.title,
                            "abstract": (resource.description or "")[:500],
                        },
                    },
                }
            }
            item_response = requests.post(items_url, json=item_data, headers=headers)
            item_response.raise_for_status()
        return list_id

    def get_list(self, list_id: str) -> TalisList:
        url = f"{TALIS_API_URL}{self.tenant}/lists/{list_id}"
        headers = self._headers()
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        items = []
        for idx, item_data in enumerate(data.get('items', []), start=1):
            identifiers = item_data.get('identifiers', {})
            items.append(TalisItem(
                position=idx,
                section=item_data.get('section'),
                importance=item_data.get('importance'),
                item_type=item_data.get('resource_type'),
                title=item_data.get('title', ''),
                authors=item_data.get('authors'),
                isbn=identifiers.get('isbn'),
                doi=identifiers.get('doi'),
                url=item_data.get('url'),
                notes=item_data.get('note'),
            ))
        return TalisList(
            identifier=list_id,
            title=data.get('title'),
            module_code=data.get('module_code'),
            academic_year=data.get('academic_year'),
            source_type='api',
            items=items,
            raw_payload_ref=url,
        )

    def add_item_to_list(self, list_id: str, resource, position: Optional[int] = None) -> dict:
        url = f"{TALIS_API_URL}{self.tenant}/lists/{list_id}/items"
        headers = self._headers()
        payload = {
            "data": {
                "type": "items",
                "attributes": {
                    "uri": resource.url,
                    "meta": {
                        "title": resource.title,
                        "abstract": (resource.description or "")[:500],
                    },
                },
            }
        }
        if position is not None:
            payload["data"]["attributes"]["position"] = position
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ========== HELPER FUNCTIONS ==========
def parse_csv_to_talis_list(file_obj: TextIO) -> TalisList:
    reader = csv.DictReader(
        (line.decode("utf-8") if isinstance(line, bytes) else line for line in file_obj)
    )
    items: List[TalisItem] = []
    list_title: Optional[str] = None
    module_code: Optional[str] = None
    academic_year: Optional[str] = None

    for idx, row in enumerate(reader, start=1):
        title = (row.get("Title") or row.get("Item Title") or "").strip()
        if not title:
            continue
        items.append(
            TalisItem(
                position=idx,
                section=(row.get("Section") or "").strip() or None,
                importance=(row.get("Importance") or "").strip() or None,
                item_type=(row.get("Resource type") or row.get("Type") or "").strip() or None,
                title=title,
                authors=(row.get("Author") or row.get("Authors") or "").strip() or None,
                isbn=(row.get("ISBN") or "").strip() or None,
                doi=(row.get("DOI") or "").strip() or None,
                url=(row.get("Web address") or row.get("URL") or "").strip() or None,
                notes=(row.get("Note for Student") or row.get("Notes") or "").strip() or None,
            )
        )
        if not list_title:
            list_title = (row.get("List name") or row.get("Reading list") or "").strip() or None
        if not module_code:
            module_code = (row.get("Module code") or row.get("Course code") or "").strip() or None
        if not academic_year:
            academic_year = (row.get("Year") or row.get("Academic year") or "").strip() or None

    talis_list = TalisList(
        identifier="csv_import",
        title=list_title,
        module_code=module_code,
        academic_year=academic_year,
        source_type="csv",
        items=items,
    )
    logger.info("Parsed CSV into TalisList with %s items", len(items))
    return talis_list


# ========== RDF/JSON PARSING HELPERS ==========

# RDF type URI to normalized string mappings
RDF_TYPE_MAPPINGS = {
    # BIBO (Bibliographic Ontology)
    "http://purl.org/ontology/bibo/Book": "book",
    "http://purl.org/ontology/bibo/Article": "article",
    "http://purl.org/ontology/bibo/Dataset": "dataset",
    "http://purl.org/ontology/bibo/Standards": "standard",
    "http://purl.org/ontology/bibo/Document": "document",
    "http://purl.org/ontology/bibo/ChapterArticle": "chapter",
    "http://purl.org/ontology/bibo/ThesisDegree": "thesis",
    "http://purl.org/ontology/bibo/Journal": "journal",
    # Schema.org types
    "https://schema.org/Book": "book",
    "https://schema.org/Article": "article",
    "https://schema.org/Dataset": "dataset",
    "https://schema.org/ScholarlyArticle": "article",
    "https://schema.org/Thesis": "thesis",
    # Dublin Core fallback
    "http://purl.org/dc/terms/BibliographicResource": "resource",
    # Add more as needed for specific Talis sources
}


def _extract_language_code(value: Any) -> Optional[str]:
    """
    Extract language code from RDF value.
    
    Handles:
      - URI like http://lexvo.org/id/iso639-3/eng → "eng"
      - URI like http://lexvo.org/id/iso639-1/en → "en"
      - Plain language code like "en" or "de" → as-is
      
    Args:
        value: RDF value (dict, list, or string)
        
    Returns:
        Language code (e.g., "en", "de", "eng") or None
    """
    extracted = _extract_rdf_value(value)
    if not extracted:
        return None
    
    # If it's a URI, extract the last segment
    if extracted.startswith("http://"):
        code = extracted.rstrip("/").split("/")[-1]
        logger.debug(f"Extracted language code: {code} from {extracted}")
        return code if code else None
    
    # Otherwise return as-is (plain language code)
    return extracted


def _normalize_publication_year(value: Any) -> Optional[str]:
    """
    Extract 4-digit publication year from RDF date value.
    
    Handles:
      - "2023" → "2023"
      - "2023-01-15" → "2023"
      - "published 2024" → "2024"
      - Invalid or absent dates → None
      
    Args:
        value: RDF value (dict, list, or string)
        
    Returns:
        4-digit year as string or None
    """
    extracted = _extract_rdf_value(value)
    if not extracted:
        return None
    
    # Use regex to find first 4-digit number
    match = re.search(r'\d{4}', extracted)
    if match:
        year = match.group(0)
        logger.debug(f"Extracted year {year} from {extracted}")
        return year
    
    return None


def _normalize_type(value: Any) -> Optional[str]:
    """
    Normalize RDF type URI to a human-readable type string.
    
    Maps standard BIBO and Schema.org URIs to lowercase strings (e.g., "book", "article").
    Falls back to extracting the last URI segment and lowercasing it.
    
    Args:
        value: RDF type URI (dict, list, or string)
        
    Returns:
        Normalized type string (lowercase) or None
    """
    extracted = _extract_rdf_value(value)
    if not extracted:
        return None
    
    # Check if it matches a known mapping
    if extracted in RDF_TYPE_MAPPINGS:
        normalized = RDF_TYPE_MAPPINGS[extracted]
        logger.debug(f"Normalized type {extracted} → {normalized}")
        return normalized
    
    # Fallback: extract last URI segment and lowercase it
    if extracted.startswith("http://"):
        type_str = extracted.rstrip("/").split("/")[-1].lower()
        logger.debug(f"Normalized type {extracted} → {type_str} (fallback)")
        return type_str if type_str else None
    
    # If it's a plain string, just lowercase it
    normalized = extracted.lower()
    logger.debug(f"Normalized type {extracted} → {normalized}")
    return normalized


def _extract_rdf_value(value_expr: Any) -> Optional[str]:
    """
    Extract a string value from RDF/JSON format.
    
    Handles:
      - {"type": "literal", "value": "string"} → "string"
      - [{"type": "literal", "value": "string"}] → "string"
      - plain string → string
      - None → None
    
    Args:
        value_expr: RDF/JSON value expression or list of expressions
        
    Returns:
        Extracted string value or None
    """
    if value_expr is None:
        return None
    
    # If it's a list, extract from the first element
    if isinstance(value_expr, list):
        if not value_expr:
            return None
        value_expr = value_expr[0]
    
    # If it's a dictionary with 'value' key
    if isinstance(value_expr, dict):
        val = value_expr.get('value')
        if val is not None:
            return str(val).strip() if val else None
        return None
    
    # If it's already a string
    if isinstance(value_expr, str):
        return value_expr.strip() if value_expr else None
    
    return None


def _extract_ordered_list_uris(rdf_node: Dict[str, Any]) -> List[str]:
    """
    Extract URIs from an RDF-ordered list representation.
    
    RDF ordered lists use predicates like:
      http://www.w3.org/1999/02/22-rdf-syntax-ns#_1
      http://www.w3.org/1999/02/22-rdf-syntax-ns#_2
      ... etc
    
    Args:
        rdf_node: A dictionary of RDF properties for a single node
        
    Returns:
        List of URIs in order, or empty list if no ordered list found
    """
    uris = []
    position = 1
    max_depth = 1000  # Safety limit to prevent infinite loops
    
    while position <= max_depth:
        predicate = f"http://www.w3.org/1999/02/22-rdf-syntax-ns#_{position}"
        
        if predicate not in rdf_node:
            break
        
        values = rdf_node[predicate]
        if not values or not isinstance(values, list):
            break
        
        # values is typically [{"type": "uri", "value": "http://..."}]
        for val_dict in values:
            if isinstance(val_dict, dict):
                uri = val_dict.get('value')
                if uri:
                    uris.append(uri)
            elif isinstance(val_dict, str):
                uris.append(val_dict)
        
        position += 1
    
    return uris


def _extract_item_from_multi_node_json(item_data: Dict[str, Any], item_uri: str) -> Optional[TalisItem]:
    """
    Extract metadata from a Talis API item JSON response.
    
    Talis returns multi-node RDF/JSON with:
    - Item node (minimal data, mostly links)
    - Resource node (book metadata: title, ISBN, authors)
    - Person nodes (referenced as creators)
    
    This function finds the resource node and extracts all item metadata.
    """
    logger.debug(f"[multi_node] Processing item URI: {item_uri}")
    
    # Verify item node exists
    if item_uri not in item_data:
        logger.warning(f"[multi_node] Item URI not found in response: {item_uri}")
        return None
    
    item_node = item_data[item_uri]
    
    # Verify it's an item by RDF type
    item_type_vals = item_node.get('http://www.w3.org/1999/02/22-rdf-syntax-ns#type', [])
    is_item = any(
        v.get('value', '').endswith('Item') 
        for v in item_type_vals 
        if isinstance(v, dict)
    )
    if not is_item:
        logger.warning(f"[multi_node] Not an Item node (type check failed)")
        return None
    
    logger.debug(f"[multi_node] Item node verified")
    
    # Find resource node with title
    resource_node = None
    resource_uri = None
    
    for node_uri, node_data in item_data.items():
        if not isinstance(node_data, dict):
            continue
        
        # Log what we're examining for debugging
        node_keys = list(node_data.keys())
        logger.debug(f"[multi_node] Checking node: {node_uri[:60]}..., keys: {len(node_keys)} properties")
        
        # Accept the first node with a title as the resource node
        if 'http://purl.org/dc/terms/title' in node_data:
            resource_uri = node_uri
            resource_node = node_data
            logger.debug(f"[multi_node] Found resource node (by title): {resource_uri[:60]}...")
            break
    
    if not resource_node:
        logger.warning(f"[multi_node] No resource node found (no nodes with title)")
        return None
    
    # Extract title (required)
    title = _extract_rdf_value(resource_node.get('http://purl.org/dc/terms/title'))
    if not title:
        logger.warning(f"[multi_node] Resource node has no extractable title")
        return None
    
    logger.debug(f"[multi_node] Title found: {title[:60]}...")
    
    # Extract ISBN
    isbn = _extract_rdf_value(resource_node.get('http://purl.org/ontology/bibo/isbn13')) or \
           _extract_rdf_value(resource_node.get('http://purl.org/ontology/bibo/isbn'))
    
    # Extract DOI
    doi = _extract_rdf_value(resource_node.get('http://purl.org/ontology/bibo/doi'))
    
    # Extract URL (try multiple predicates)
    url = _extract_rdf_value(resource_node.get('http://purl.org/dc/terms/identifier')) or \
          _extract_rdf_value(resource_node.get('http://purl.org/dc/terms/source')) or \
          _extract_rdf_value(resource_node.get('http://www.w3.org/2000/01/rdf-schema#seeAlso'))
    
    # Extract authors by resolving creator URIs to person nodes
    authors = None
    creator_refs = resource_node.get('http://purl.org/dc/terms/creator', [])
    
    if creator_refs:
        author_names = []
        
        if isinstance(creator_refs, list):
            for creator_entry in creator_refs:
                creator_uri = creator_entry.get('value') if isinstance(creator_entry, dict) else creator_entry
                
                if creator_uri and creator_uri in item_data:
                    creator_node = item_data[creator_uri]
                    if isinstance(creator_node, dict):
                        # Extract FOAF name (firstName + surname)
                        first = _extract_rdf_value(creator_node.get('http://xmlns.com/foaf/0.1/firstName'))
                        last = _extract_rdf_value(creator_node.get('http://xmlns.com/foaf/0.1/surname'))
                        
                        if first and last:
                            author_names.append(f"{first} {last}")
                        elif first:
                            author_names.append(first)
                        elif last:
                            author_names.append(last)
        
        if author_names:
            authors = ", ".join(author_names)
            logger.debug(f"[multi_node] Authors: {authors}")
    
    # Extract publisher
    publisher = _extract_rdf_value(resource_node.get('http://purl.org/dc/terms/publisher'))
    if publisher:
        logger.debug(f"[multi_node] Publisher: {publisher}")
    
    # Extract publication year
    publication_year = _normalize_publication_year(
        resource_node.get('http://purl.org/dc/terms/date')
    ) or _normalize_publication_year(
        resource_node.get('http://purl.org/ontology/bibo/issued')
    )
    if publication_year:
        logger.debug(f"[multi_node] Publication year: {publication_year}")
    
    # Extract language
    language = _extract_language_code(resource_node.get('http://purl.org/dc/terms/language'))
    if language:
        logger.debug(f"[multi_node] Language: {language}")
    
    # Extract and normalize type
    normalised_type = _normalize_type(resource_node.get('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'))
    if normalised_type:
        logger.debug(f"[multi_node] Normalised type: {normalised_type}")
    
    # Return item (position will be set by caller)
    result = TalisItem(
        title=title,
        position=None,
        section=None,
        importance=None,
        item_type=None,
        authors=authors,
        isbn=isbn,
        doi=doi,
        url=url,
        notes=None,
        publisher=publisher,
        publication_year=publication_year,
        language=language,
        normalised_type=normalised_type,
    )
    
    # Debug: log all resource node keys for future adjustments
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"[multi_node] Resource node available keys: {list(resource_node.keys())}")
        logger.debug(f"[multi_node] Extracted TalisItem: {result}")
    
    logger.debug(f"[multi_node] Item complete: {title}")
    return result


def fetch_list_from_url(list_url: str) -> TalisList:
    """
    Fetches a Talis reading list using the unauthenticated Linked Data API.
    Extracts items directly from the 'contains' array, handling both sections and items.
    """
    import re

    # Extract list UUID and tenant
    match = re.search(r'/lists/([a-fA-F0-9-]+)', list_url)
    if not match:
        raise ValueError(f"Could not extract list UUID from URL: {list_url}")
    list_uuid = match.group(1)

    tenant_match = re.search(r'/(?:3|\d+)/([^/]+)/lists/', list_url)
    tenant = tenant_match.group(1) if tenant_match else os.getenv("TALIS_TENANT", "mmu")

    json_url = f"https://{tenant}.rl.talis.com/lists/{list_uuid}.json"
    logger.info("Fetching Talis list from unauthenticated API: %s", json_url)

    response = requests.get(json_url, timeout=15)
    response.raise_for_status()
    data = response.json()

    # The top-level key is the list URI
    if len(data) != 1:
        raise ValueError("Unexpected JSON structure: not a single URI node")
    list_uri = next(iter(data))
    list_node = data[list_uri]

    # Extract list title
    title = _extract_rdf_value(list_node.get('http://purl.org/dc/terms/title')) or \
            _extract_rdf_value(list_node.get('http://rdfs.org/sioc/spec/name'))

    # Get the 'contains' array - try both standard predicate and RDF-ordered lists
    contains = list_node.get('http://purl.org/vocab/resourcelist/schema#contains', [])
    
    # If no contains, check for RDF-ordered list properties (#_1, #_2, etc.)
    if not contains:
        contains = []
        pos = 1
        while True:
            rdf_key = f"http://www.w3.org/1999/02/22-rdf-syntax-ns#_{pos}"
            if rdf_key not in list_node:
                break
            val = list_node[rdf_key]
            if isinstance(val, list):
                contains.extend(val)
            pos += 1
        
        if not contains:
            logger.warning("No 'contains' array or RDF-ordered list found in list node")
            return TalisList(
                identifier=list_uri,
                title=title,
                module_code=None,
                academic_year=None,
                source_type='api',
                items=[],
                raw_payload_ref=json_url,
            )

    items = []
    # We'll process URIs in order (they may already be in correct sequence)
    for entry in contains:
        uri = entry.get('value') if isinstance(entry, dict) else entry
        if not uri:
            continue

        # Determine if it's an item or a section by path
        if '/items/' in uri:
            # It's an item – fetch its JSON
            try:
                logger.debug(f"Fetching item JSON: {uri}")
                item_resp = requests.get(f"{uri}.json", timeout=10)
                if item_resp.status_code != 200:
                    logger.warning(f"Failed to fetch item {uri}: HTTP {item_resp.status_code}")
                    continue
                item_data = item_resp.json()
                
                # Use helper to extract from multi-node response
                item_obj = _extract_item_from_multi_node_json(item_data, uri)
                if item_obj:
                    item_obj.position = len(items) + 1
                    items.append(item_obj)
                    logger.debug(f"Added item #{item_obj.position}: {item_obj.title}")
                else:
                    logger.debug(f"Item extraction failed for {uri}")
            except Exception as e:
                logger.warning(f"Error processing item {uri}: {e}")
                continue

        elif '/sections/' in uri:
            # It's a section – fetch its JSON and look for its own 'contains' array or RDF-ordered lists
            try:
                section_resp = requests.get(f"{uri}.json", timeout=10)
                if section_resp.status_code != 200:
                    logger.warning(f"Failed to fetch section {uri}: HTTP {section_resp.status_code}")
                    continue
                section_data = section_resp.json()
                section_uri_key = next(iter(section_data))
                section_node = section_data[section_uri_key]

                section_contains = section_node.get('http://purl.org/vocab/resourcelist/schema#contains', [])
                
                # If no contains, check for RDF-ordered list properties
                if not section_contains:
                    section_contains = []
                    pos = 1
                    while True:
                        rdf_key = f"http://www.w3.org/1999/02/22-rdf-syntax-ns#_{pos}"
                        if rdf_key not in section_node:
                            break
                        val = section_node[rdf_key]
                        if isinstance(val, list):
                            section_contains.extend(val)
                        pos += 1
                
                for sub_entry in section_contains:
                    sub_uri = sub_entry.get('value') if isinstance(sub_entry, dict) else sub_entry
                    if sub_uri and '/items/' in sub_uri:
                        # Recursively fetch the item
                        try:
                            sub_resp = requests.get(f"{sub_uri}.json", timeout=10)
                            if sub_resp.status_code != 200:
                                continue
                            sub_data = sub_resp.json()
                            sub_uri_key = next(iter(sub_data))
                            sub_node = sub_data[sub_uri_key]

                            sub_title = _extract_rdf_value(sub_node.get('http://purl.org/dc/terms/title')) or \
                                        _extract_rdf_value(sub_node.get('http://purl.org/dc/elements/1.1/title'))
                            if not sub_title:
                                continue

                            # Extract creator - handle FOAF structure with firstName + surname
                            sub_authors = None
                            creator_field = sub_node.get('http://purl.org/dc/terms/creator')
                            if creator_field:
                                authors_list = []
                                if isinstance(creator_field, list):
                                    for creator_entry in creator_field:
                                        author_name = _extract_rdf_value(creator_entry)
                                        if author_name:
                                            authors_list.append(author_name)
                                if authors_list:
                                    sub_authors = ", ".join(authors_list)

                            sub_isbn = _extract_rdf_value(sub_node.get('http://purl.org/ontology/bibo/isbn')) or \
                                       _extract_rdf_value(sub_node.get('http://purl.org/ontology/bibo/isbn13'))
                            sub_doi = _extract_rdf_value(sub_node.get('http://purl.org/ontology/bibo/doi'))
                            sub_url = _extract_rdf_value(sub_node.get('http://www.w3.org/2000/01/rdf-schema#seeAlso')) or \
                                      _extract_rdf_value(sub_node.get('http://purl.org/dc/terms/identifier'))

                            items.append(TalisItem(
                                position=len(items) + 1,
                                section=None,
                                importance=None,
                                item_type=None,
                                title=sub_title,
                                authors=sub_authors,
                                isbn=sub_isbn,
                                doi=sub_doi,
                                url=sub_url,
                                notes=None,
                            ))
                            logger.debug(f"Added item from section: {sub_title}")
                        except Exception as e:
                            logger.warning(f"Error processing sub-item {sub_uri}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Error processing section {uri}: {e}")
                continue
        else:
            logger.warning(f"Unknown URI type: {uri}")

    logger.info("Fetched Talis list '%s' from API with %d items", title or list_uuid, len(items))
    return TalisList(
        identifier=list_uri,
        title=title,
        module_code=None,
        academic_year=None,
        source_type='api',
        items=items,
        raw_payload_ref=json_url,
    )