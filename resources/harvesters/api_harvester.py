import requests
import logging
import time

from django.core.exceptions import ValidationError

from resources.harvesters.utils import request_with_retry
from resources.harvesters.base_harvester import BaseHarvester
from resources.harvesters.ingestion import ingest_record_dict


logger = logging.getLogger(__name__)


def _normalise_language(raw: str) -> str:
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


def _normalise_resource_type(raw_type: str) -> str:
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


class APIHarvester(BaseHarvester):
    def __init__(self, source):
        super().__init__(source)
        self.config = self._get_config()

    def _get_config(self):
        """Extract configuration from source model."""
        # Support configurable timeout via source.request_params['timeout'] or default to 180s
        timeout = 180
        params = getattr(self.source, "request_params", {}) or {}
        if params and "timeout" in params:
            try:
                timeout = int(params["timeout"])
            except (ValueError, TypeError):
                pass

        return {
            "base_url": getattr(self.source, "api_endpoint", None),
            "api_key": getattr(self.source, "api_key", None),
            "headers": getattr(self.source, "request_headers", {}) or {},
            "params": params,
            "timeout": timeout,
        }

    def test_connection(self):
        """Test connection to API endpoint."""
        try:
            config = self._get_config()
            test_url = f"{config['base_url']}"
            if "?" not in test_url:
                test_url += "?limit=1"

            headers = config.get("headers", {})
            params = config.get("params", {})

            try:
                resp = self.request(
                    "get",
                    test_url,
                    headers=headers,
                    params=params,
                    timeout=10,
                    max_attempts=3,
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"API connection test failed after retries: {e}")
                return False
        except Exception as e:
            logger.error(f"API connection test failed: {str(e)}")
            return False

    def fetch_and_process_records(self):
        """Fetch and process records from API, then ingest them."""
        try:
            config = self._get_config()

            url = config["base_url"]
            headers = config.get("headers", {})
            params = config.get("params", {})

            # Add API key if provided
            if config.get("api_key"):
                if "Authorization" not in headers:
                    headers["Authorization"] = f"Bearer {config['api_key']}"

            logger.info(f"Fetching API records from: {url}")
            logger.info(f"Request params: {params}")
            logger.info(f"Request headers: {headers}")

            timeout = config.get("timeout", 90)
            logger.info(f"API request timeout: {timeout}s")

            try:
                response = self.request(
                    "get",
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                    max_attempts=4,
                )
            except Exception as e:
                error_msg = f"API fetch failed: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                raise ValidationError(error_msg) from e

            logger.info(f"API response status: {response.status_code}")
            logger.info(
                "API response content-type: "
                f"{response.headers.get('content-type', 'unknown')}"
            )

            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type and "application/xml" in content_type:
                error_msg = (
                    f"API returned XML instead of JSON. Content-Type: {content_type}"
                )
                logger.error(error_msg)
                logger.error(f"Response preview: {response.text[:500]}")
                raise ValidationError(error_msg)

            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Failed to parse JSON response: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Response content preview: {response.text[:500]}")
                raise ValidationError(error_msg) from e

            records = self._process_api_response(data)

            ingested = 0
            for rec in records:
                try:
                    ingest_record_dict(self.source, rec)
                    ingested += 1
                except Exception as e:
                    logger.warning(f"Failed to ingest API record: {e}")

            logger.info(f"Ingested {ingested} resources from API")
            return records

        except ValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error in API harvest: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValidationError(error_msg) from e

    def _extract_oapen_metadata(self, metadata_list):
        """
        Extract Dublin Core metadata from OAPEN's metadata array format.

        OAPEN returns metadata as:
        [
            {"key": "dc.title", "value": "...", ...},
            {"key": "dc.creator", "value": "...", ...},
            ...
        ]

        Returns a dict mapping Dublin Core elements to values.
        """
        if not isinstance(metadata_list, list):
            return {}

        dc_map = {}
        for entry in metadata_list:
            if not isinstance(entry, dict):
                continue

            key = entry.get("key", "").lower()  # e.g., "dc.title", "dc.creator"
            value = entry.get("value", "").strip()

            if not key or not value:
                continue

            if key not in dc_map:
                dc_map[key] = value
            elif key.endswith(".author") or key.endswith(".creator"):
                dc_map[key] = dc_map[key] + "; " + value

        return dc_map

    def _process_api_response(self, data):
        """Process API response into OER resource data dicts."""
        processed_records = []

        # Handle different API response structures
        if isinstance(data, list):
            records = data
        else:
            records = (
                data.get("results")
                or data.get("items")
                or data.get("data")
                or data.get("records")
            )
            if records is None:
                records = [data] if isinstance(data, dict) and data else []

        for record in records:
            try:
                if not isinstance(record, dict):
                    continue

                # OAPEN REST API format (metadata array with dc.* keys)
                if isinstance(record.get("metadata"), list) and any(
                    isinstance(m, dict) and m.get("key", "").startswith("dc.")
                    for m in record.get("metadata", [])
                ):
                    dc_map = self._extract_oapen_metadata(record.get("metadata", []))

                    title = dc_map.get("dc.title", record.get("name", ""))
                    description = dc_map.get("dc.description", "") or dc_map.get(
                        "dc.description.abstract", ""
                    )
                    author = dc_map.get("dc.creator", "") or dc_map.get(
                        "dc.contributor.author", ""
                    )
                    subject = dc_map.get("dc.subject", "")
                    publisher = dc_map.get("dc.publisher", "")
                    license_val = dc_map.get("dc.rights", "") or dc_map.get(
                        "dc.rights.uri", ""
                    )
                    lang = dc_map.get("dc.language", "en")
                    resource_type = dc_map.get("dc.type", record.get("type", ""))

                    # Date fields: dc.date.issued preferred, then dc.date
                    raw_date = (
                        dc_map.get("dc.date.issued")
                        or dc_map.get("dc.date")
                        or ""
                    )
                    publication_year = ""
                    date_first_published = None
                    if raw_date:
                        raw_date = raw_date.strip()
                        if len(raw_date) >= 4 and raw_date[:4].isdigit():
                            publication_year = raw_date[:4]
                        if (
                            len(raw_date) >= 10
                            and raw_date[4] == "-"
                            and raw_date[7] == "-"
                        ):
                            date_first_published = raw_date

                    # Try to construct URL from handle or link
                    url = ""
                    if record.get("handle"):
                        url = f"https://hdl.handle.net/{record['handle']}"
                    elif record.get("link"):
                        url = (
                            f"https://library.oapen.org{record['link']}"
                            if record["link"].startswith("/")
                            else record["link"]
                        )

                    resource_data = {
                        "title": title,
                        "description": description,
                        "url": url,
                        "license": license_val,
                        "publisher": publisher,
                        "author": author,
                        "language": _normalise_language(lang),
                        "resource_type": resource_type,
                        "normalised_type": _normalise_resource_type(resource_type),
                        "subject": subject,
                        "publication_year": publication_year,
                        "date_first_published": date_first_published,
                    }
                else:
                    # Generic API format
                    raw_lang = record.get("language", "en")
                    raw_type = record.get("resource_type", record.get("type", ""))

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

                    # Generic date extraction for APIs like DOAB
                    raw_date = (
                        record.get("publication_date")
                        or record.get("date")
                        or record.get("published")
                        or ""
                    )
                    publication_year = ""
                    date_first_published = None
                    if raw_date:
                        raw_date = str(raw_date).strip()
                        if len(raw_date) >= 4 and raw_date[:4].isdigit():
                            publication_year = raw_date[:4]
                        if (
                            len(raw_date) >= 10
                            and raw_date[4] == "-"
                            and raw_date[7] == "-"
                        ):
                            date_first_published = raw_date

                    resource_data = {
                        "title": record.get("title", record.get("name", "")),
                        "description": record.get(
                            "description", record.get("summary", "")
                        ),
                        "url": record.get(
                            "url", record.get("link", record.get("identifier", ""))
                        ),
                        "license": record.get("license", record.get("rights", "")),
                        "publisher": record.get(
                            "publisher", record.get("provider", "")
                        ),
                        "author": record.get(
                            "author",
                            record.get("creator", record.get("owner", "")),
                        ),
                        "language": _normalise_language(raw_lang),
                        "resource_type": raw_type,
                        "normalised_type": _normalise_resource_type(raw_type),
                        "subject": subj,
                        "publication_year": publication_year,
                        "date_first_published": date_first_published,
                    }

                if resource_data["title"] and resource_data["url"]:
                    processed_records.append(resource_data)

            except Exception as e:
                logger.warning(f"Failed to process API record: {str(e)}")
                continue

        logger.info(f"Processed {len(processed_records)} records from API")
        return processed_records
