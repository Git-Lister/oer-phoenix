#!/usr/bin/env python
"""
Integration test script for new Talis features:
- Publisher, publication_year, language, normalised_type extraction
- Error handling in analysis pipeline
- Query building with new fields
"""

import logging
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oer_rebirth.settings')

import django

django.setup()

from resources.services.talis import (
    RDF_TYPE_MAPPINGS,
    TalisItem,
    _extract_language_code,
    _extract_rdf_value,
    _normalize_publication_year,
    _normalize_type,
)
from resources.services.talis_analysis import _build_query

# Setup logging to see debug output
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_extract_language_code():
    """Test language code extraction from URIs and plain codes."""
    logger.info("=== Testing _extract_language_code ===")
    
    test_cases = [
        # Input, Expected Output
        ("http://lexvo.org/id/iso639-3/eng", "eng"),
        ("http://lexvo.org/id/iso639-1/en", "en"),
        ("en", "en"),
        ("de-DE", "de-DE"),
        ({"type": "uri", "value": "http://lexvo.org/id/iso639-3/deu"}, "deu"),
        (None, None),
    ]
    
    for input_val, expected in test_cases:
        result = _extract_language_code(input_val)
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} Input: {input_val!r} → Output: {result!r} (Expected: {expected!r})")
        assert result == expected, f"Failed for {input_val}"


def test_normalize_publication_year():
    """Test publication year extraction from various date formats."""
    logger.info("\n=== Testing _normalize_publication_year ===")
    
    test_cases = [
        ("2023", "2023"),
        ("2023-01-15", "2023"),
        ("published 2024", "2024"),
        ({"type": "literal", "value": "2022-06"}, "2022"),
        ("invalid date", None),
        (None, None),
    ]
    
    for input_val, expected in test_cases:
        result = _normalize_publication_year(input_val)
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} Input: {input_val!r} → Output: {result!r} (Expected: {expected!r})")
        assert result == expected, f"Failed for {input_val}"


def test_normalize_type():
    """Test RDF type normalization."""
    logger.info("\n=== Testing _normalize_type ===")
    
    test_cases = [
        ("http://purl.org/ontology/bibo/Book", "book"),
        ("http://purl.org/ontology/bibo/Article", "article"),
        ("http://purl.org/ontology/bibo/Dataset", "dataset"),
        ("https://schema.org/Book", "book"),
        ("https://schema.org/Article", "article"),
        ("http://purl.org/ontology/bibo/UnknownType", "unknowntype"),  # Fallback
        ("book", "book"),  # Plain string
        ({"type": "uri", "value": "http://purl.org/ontology/bibo/Book"}, "book"),
        (None, None),
    ]
    
    for input_val, expected in test_cases:
        result = _normalize_type(input_val)
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} Input: {input_val!r} → Output: {result!r} (Expected: {expected!r})")
        assert result == expected, f"Failed for {input_val}"


def test_rdf_type_mappings():
    """Verify RDF_TYPE_MAPPINGS is complete and correct."""
    logger.info("\n=== Checking RDF_TYPE_MAPPINGS ===")
    
    logger.info(f"Total mappings: {len(RDF_TYPE_MAPPINGS)}")
    for uri, normalized in list(RDF_TYPE_MAPPINGS.items())[:5]:
        logger.info(f"  {uri} → {normalized}")
    logger.info(f"  ... and {len(RDF_TYPE_MAPPINGS) - 5} more")
    
    # Verify all values are lowercase
    for uri, normalized in RDF_TYPE_MAPPINGS.items():
        assert normalized == normalized.lower(), f"Value not lowercase: {normalized}"
    
    logger.info("✓ All mappings are valid (lowercase strings)")


def test_build_query_with_new_fields():
    """Test query building includes new fields."""
    logger.info("\n=== Testing _build_query with new fields ===")
    
    # Item without new fields
    item1 = TalisItem(
        title="Biology Basics",
        authors="John Smith",
    )
    query1 = _build_query(item1)
    logger.info(f"Item 1 (no new fields): {query1!r}")
    assert "Biology Basics" in query1
    assert "John Smith" in query1
    
    # Item with all fields
    item2 = TalisItem(
        title="Advanced Chemistry",
        authors="Jane Doe, Robert Jones",
        isbn="978-0-12345-678-9",
        doi="10.1234/example",
        publisher="Academic Press",
        publication_year="2023",
    )
    query2 = _build_query(item2)
    logger.info(f"Item 2 (all fields): {query2!r}")
    assert "Advanced Chemistry" in query2
    assert "Jane Doe" in query2
    assert "ISBN 978-0-12345-678-9" in query2
    assert "DOI 10.1234/example" in query2
    assert "Publisher Academic Press" in query2
    assert "2023" in query2
    logger.info("✓ Query building includes publisher and publication_year")


def test_talis_item_with_new_fields():
    """Verify TalisItem can hold all new fields."""
    logger.info("\n=== Testing TalisItem with new fields ===")
    
    item = TalisItem(
        title="Test Item",
        authors="Test Author",
        publisher="Test Publisher",
        publication_year="2023",
        language="en",
        normalised_type="book",
    )
    
    logger.info(f"Title: {item.title}")
    logger.info(f"Authors: {item.authors}")
    logger.info(f"Publisher: {item.publisher}")
    logger.info(f"Publication Year: {item.publication_year}")
    logger.info(f"Language: {item.language}")
    logger.info(f"Normalised Type: {item.normalised_type}")
    
    assert item.publisher == "Test Publisher"
    assert item.publication_year == "2023"
    assert item.language == "en"
    assert item.normalised_type == "book"
    logger.info("✓ All new fields are correctly stored")


def main():
    """Run all tests."""
    logger.info("Starting integration tests for new Talis features\n")
    
    try:
        test_rdf_type_mappings()
        test_extract_language_code()
        test_normalize_publication_year()
        test_normalize_type()
        test_talis_item_with_new_fields()
        test_build_query_with_new_fields()
        
        logger.info("\n" + "="*50)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("="*50)
        return 0
    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
