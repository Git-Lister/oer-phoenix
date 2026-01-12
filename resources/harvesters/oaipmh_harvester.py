import logging
from xml.etree import ElementTree as ET
import time
from urllib.parse import urlencode
from resources.harvesters.utils import request_with_retry
from resources.harvesters.base_harvester import BaseHarvester
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


def _pick_primary_url(value):
    """
    From a dc:identifier value that might be:
    - a single string
    - a list of strings
    return the best http(s) URL, preferring direct PDFs, or ''.
    """
    if not value:
        return ""

    if isinstance(value, list):
        candidates = value
    else:
        candidates = [str(value)]

    http_urls = [
        v.strip()
        for v in candidates
        if isinstance(v, str) and v.lower().startswith(("http://", "https://"))
    ]
    if not http_urls:
        return ""

    # Prefer any PDF link if present
    for v in http_urls:
        if v.lower().endswith(".pdf") or ".pdf" in v.lower():
            return v

    # Otherwise, fall back to the first http(s) URL (e.g. DOAB or OAPEN landing page)
    return http_urls[0]


def _normalise_language(raw: str) -> str:
    """Normalise dc:language values to ISO 639-1 where possible."""
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


def _normalise_resource_type(raw_type: str) -> str:
    if not raw_type:
        return ""
    t = str(raw_type).strip().lower()

    # OAPEN / DOAB specific strings
    if t in ("book", "monograph", "text", "book (monograph)"):
        return "book"
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


class OAIHarvester(BaseHarvester):
    # Dublin Core namespace
    DC_NS = "http://purl.org/dc/elements/1.1/"
    
    def __init__(self, source):
        super().__init__(source)
        self.config = self._get_config()

    def _get_config(self):
        # Prefer explicit `oaipmh_url` field; fall back to other common names
        return {
            "base_url": getattr(self.source, "oaipmh_url", None)
            or getattr(self.source, "api_endpoint", None)
            or getattr(self.source, "api_url", None)
            or getattr(self.source, "oai_endpoint", None),
            "metadata_prefix": (getattr(self.source, "request_params", {}) or {}).get(
                "metadataPrefix", "oai_dc"
            ),
            "headers": getattr(self.source, "request_headers", {}) or {},
            "params": getattr(self.source, "request_params", {}) or {},
        }

    def test_connection(self):
        config = self._get_config()
        try:
            url = f"{config['base_url']}?verb=Identify"
            resp = request_with_retry(
                "get", url, headers=config.get("headers", {}), timeout=10, max_attempts=3
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _parse_record(self, record_xml):
        """Parse OAI-PMH record with complete Dublin Core field extraction."""
        
        # Helper to extract DC field (namespace-aware + fallback)
        def get_dc_field(field_name):
            """Extract Dublin Core field, return list of non-empty values."""
            values = []
            # Try with DC namespace
            for elem in record_xml.findall(f".//{{{self.DC_NS}}}{field_name}"):
                if elem.text and elem.text.strip():
                    values.append(elem.text.strip())
            # Fallback to unnamespaced
            if not values:
                for elem in record_xml.findall(f".//{field_name}"):
                    if elem.text and elem.text.strip():
                        values.append(elem.text.strip())
            return values
        
        # Title
        titles = get_dc_field('title')
        title = titles[0] if titles else None
        
        # Identifier (URL)
        identifiers = get_dc_field('identifier')
        primary_url = _pick_primary_url(identifiers)
        
        # Description
        descriptions = get_dc_field('description')
        description = descriptions[0] if descriptions else None
        
        # Type
        types = get_dc_field('type')
        resource_type = types[0] if types else ""
        normalised_type = _normalise_resource_type(resource_type)
        
        # Language
        languages = get_dc_field('language')
        lang = _normalise_language(languages[0]) if languages else "en"
        
        # Subject extraction (with license filtering)
        subjects = get_dc_field('subject')
        # Filter out license-related subjects (often misplaced dc:rights)
        LICENSE_KEYWORDS = ['creative commons', 'cc by', 'cc0', 'public domain', 'open access']
        clean_subjects = [
            s for s in subjects 
            if not any(kw in s.lower() for kw in LICENSE_KEYWORDS)
        ]
        subject = ', '.join(clean_subjects[:3]) if clean_subjects else ''  # Top 3 subjects
        
        # License extraction (dc:rights)
        rights = get_dc_field('rights')
        license_info = rights[0] if rights else ''  # Take first rights statement
        
        # Publisher extraction
        publishers = get_dc_field('publisher')
        publisher = publishers[0] if publishers else ''
        
        # Author extraction (dc:creator)
        creators = get_dc_field('creator')
        author = ', '.join(creators[:2]) if creators else ''  # Top 2 authors
        
        return {
            "title": title,
            "url": primary_url,
            "description": description,
            "subject": subject,
            "license": license_info,
            "publisher": publisher,
            "author": author,
            "resource_type": resource_type,
            "normalised_type": normalised_type,
            "language": lang,
        }

    def fetch_and_process_records(self):
        config = self._get_config()
        base = config["base_url"]
        metadata_prefix = config.get("metadata_prefix", "oai_dc")
        params = config.get("params", {}) or {}

        records = []
        resumption_token = None
        while True:
            query_params = {}
            if resumption_token:
                query_params["verb"] = "ListRecords"
                query_params["resumptionToken"] = resumption_token
            else:
                query_params = {
                    "verb": "ListRecords",
                    "metadataPrefix": metadata_prefix,
                }
                query_params.update(params)

            url = f"{base}?{urlencode(query_params)}"
            try:
                resp = self.request(
                    "get",
                    url,
                    headers=config.get("headers", {}),
                    timeout=30,
                    max_attempts=4,
                )
            except Exception as e:
                logger.error(f"Failed to fetch OAI-PMH records: {e}")
                raise ValidationError(
                    f"Failed to fetch OAI-PMH records: {e}"
                ) from e

            try:
                content = resp.content

                # If the response is HTML or contains wrapping, try to extract the OAI-PMH XML block
                ct = ""
                try:
                    ct = resp.headers.get("content-type", "")
                except Exception:
                    pass

                if isinstance(content, (bytes, bytearray)):
                    lower = content.lower()
                    if (
                        b"<html" in lower
                        or b"<!doctype html" in lower
                        or "html" in ct.lower()
                    ):
                        # attempt to extract the OAI-PMH XML fragment
                        start = content.find(b"<OAI-PMH")
                        end = content.rfind(b"</OAI-PMH>")
                        if start != -1 and end != -1:
                            content = content[start : end + 10]
                        else:
                            logger.error(
                                "Non-XML/HTML OAI response received; aborting parse"
                            )
                            raise ValidationError(
                                "Non-XML response received from OAI endpoint"
                            )

                root = ET.fromstring(content)
            except Exception as e:
                logger.error(f"Failed to parse OAI response XML: {e}")
                raise ValidationError(
                    f"Failed to parse OAI response XML: {e}"
                ) from e

            for rec in root.findall(
                ".//{http://www.openarchives.org/OAI/2.0/}record"
            ):
                try:
                    parsed = self._parse_record(rec)
                    if parsed.get("url") or parsed.get("title"):
                        records.append(parsed)
                except Exception:
                    logger.exception("Failed to parse record")

            # look for resumptionToken
            rt = root.find(
                ".//{http://www.openarchives.org/OAI/2.0/}resumptionToken"
            )
            if (rt is None or (rt.text is None or rt.text.strip() == "")):
                break
            resumption_token = rt.text

        return records


# Backwards compatibility: some code/tests expect `OAIPMHHarvester`
OAIPMHHarvester = OAIHarvester
