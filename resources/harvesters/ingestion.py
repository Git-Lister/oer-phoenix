# resources/harvesters/ingestion.py
from __future__ import annotations

from typing import Any, Dict

from resources.models import OERResource

ALLOWED_TYPES = {"book", "chapter", "article", "video", "course", "other"}


def coerce_normalised_type(raw: Any) -> str | None:
    """
    Ensure normalised_type is one of the allowed internal codes.
    Anything else becomes None (→ Unspecified).
    """
    if not raw:
        return None
    raw_str = str(raw).strip().lower()
    return raw_str if raw_str in ALLOWED_TYPES else None


def ingest_record_dict(source, data: Dict[str, Any]) -> OERResource:
    """
    Take a single harvested record dict and upsert an OERResource.

    Expected keys (best-effort):
      title, url, description, license, publisher, author,
      language, resource_type, normalised_type, subject,
      isbn, issn, oclc_number, doi,
      publication_year, date_first_published.
    """
    url = (data.get("url") or "").strip()
    if not url:
        # Defensive: do not create URL-less resources
        raise ValueError("Cannot ingest record without a URL")

    normalised_type = coerce_normalised_type(data.get("normalised_type"))
    resource_type = (data.get("resource_type") or "").strip()

    obj, _created = OERResource.objects.update_or_create(
        source=source,
        url=url,
        defaults={
            "title": data.get("title") or "",
            "description": data.get("description") or "",
            "license": data.get("license") or "",
            "publisher": data.get("publisher") or "",
            "author": data.get("author") or "",
            "language": data.get("language") or "en",
            "subject": data.get("subject") or "",
            "resource_type": resource_type,
            "normalised_type": normalised_type,
            "isbn": data.get("isbn") or "",
            "issn": data.get("issn") or "",
            "oclc_number": data.get("oclc_number") or "",
            "doi": data.get("doi") or "",
            "publication_year": data.get("publication_year") or "",
            "date_first_published": data.get("date_first_published") or None,
            "is_active": True,
        },
    )
    return obj
