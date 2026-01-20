"""
Description enrichment utilities for OER resources.

Helps identify and fix boilerplate or weak descriptions that don't provide
useful information for search, recommendations, or embeddings.
"""

BOILERPLATE_SNIPPETS = [
    "creative commons attribution (cc by) | ebook. published by springer nature",
    "cc by ebook published by springer",
    "springer nature",
    # Add other known boilerplate strings as discovered
]


def is_boilerplate_description(text: str | None) -> bool:
    """
    Check if a description is too generic or boilerplate to be useful.
    
    Args:
        text: Description text to check
        
    Returns:
        True if description is empty, None, or matches a known boilerplate pattern
    """
    if not text:
        return True
    
    # Normalize whitespace and convert to lowercase for comparison
    normalized = " ".join(text.strip().lower().split())
    
    # Check against known boilerplate patterns
    for snippet in BOILERPLATE_SNIPPETS:
        normalized_snippet = " ".join(snippet.strip().lower().split())
        if normalized == normalized_snippet:
            return True
    
    # Check if description is too short to be useful
    if len(text.strip()) < 20:
        return True
    
    return False


def extract_description_from_html(html_text: str) -> str | None:
    """
    Extract a useful description from HTML content.
    
    Tries multiple strategies:
    1. Meta description tag
    2. Open Graph description
    3. First substantial paragraph
    
    Args:
        html_text: HTML content as string
        
    Returns:
        Best available description, or None if nothing suitable found
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Fallback if BeautifulSoup not available
        return None
    
    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return None
    
    desc = None
    
    # Try 1: Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        content = meta.get("content")
        if content:
            content_str = (content[0] if isinstance(content, list) else content)
            if content_str:
                desc = content_str.strip()
    
    # Try 2: Open Graph description
    if not desc:
        og = soup.find("meta", attrs={"property": "og:description"})
        if og and og.get("content"):
            content = og.get("content")
            if content:
                content_str = (content[0] if isinstance(content, list) else content)
                if content_str:
                    desc = content_str.strip()
    
    # Try 3: First substantial paragraph
    if not desc:
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            # Skip tiny fragments and navigation text
            if len(text) > 100:
                desc = text
                break
    
    # Try 4: Any substantial text block
    if not desc:
        for div in soup.find_all("div", class_=["content", "main", "description", "abstract"]):
            text = div.get_text(" ", strip=True)
            if len(text) > 100:
                desc = text
                break
    
    # Validate and clean
    if desc and len(desc) >= 50:
        # Truncate to reasonable length (2000 chars)
        return desc[:2000]
    
    return None
