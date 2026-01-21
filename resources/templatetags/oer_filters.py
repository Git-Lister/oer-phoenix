from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def star_rating(score):
    """Convert quality score to star rating display."""
    if not score or score == 0:
        return mark_safe('<span class="text-muted">Not rated</span>')

    stars = int(score)
    half_star = (score - stars) >= 0.5
    empty_stars = 5 - stars - (1 if half_star else 0)

    html = '<span class="text-warning">'
    html += '★' * stars
    if half_star:
        html += '½'
    html += ' ' + '☆' * empty_stars + '</span>'
    html += f' <span class="text-muted">({score:.1f})</span>'
    return mark_safe(html)


@register.filter
def multiply(value, arg):
    """
    Multiply numeric value by arg.

    Used to convert a 0–5 quality score into a 0–100 percentage in templates.
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def language_badge(language_code):
    """Display language badge for non-English resources."""
    if not language_code or language_code.lower() == "en":
        return ""

    language_names = {
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
    }
    lang_name = language_names.get(language_code.lower(), language_code.upper())
    return mark_safe(f'<span class="badge bg-secondary ms-1">{lang_name}</span>')


@register.filter
def source_badge(source):
    """Display colored badge for resource source."""
    source_colors = {
        "OAPEN": "primary",
        "DOAB": "success",
        "OpenStax": "info",
        "OER Commons": "warning",
        "MERLOT": "secondary",
        "MIT OCW": "danger",
    }

    source_name = (
        source.display_name
        if hasattr(source, "display_name") and source.display_name
        else source.name
    )
    color = source_colors.get(source_name, "secondary")
    return mark_safe(f'<span class="badge bg-{color} me-1">{source_name}</span>')


@register.filter
def match_reason_badge(reason):
    """Display badge explaining why resource was matched."""
    if not reason:
        return ""

    reason_labels = {
        "semantic": ("Semantic Match", "primary"),
        "title": ("Title Match", "success"),
        "description": ("Description Match", "info"),
        "keyword": ("Keyword Match", "warning"),
        "combined": ("Combined Match", "secondary"),
        "hybrid": ("Hybrid Match", "secondary"),
    }

    label, color = reason_labels.get(str(reason).lower(), (reason, "secondary"))
    return mark_safe(f'<span class="badge bg-{color} me-1">{label}</span>')


@register.simple_tag
def translate_button(resource):
    """Display translation button for non-English resources."""
    if (
        not resource
        or not hasattr(resource, "needs_translation")
        or not resource.needs_translation()
    ):
        return ""

    return mark_safe(
        '<button type="button" '
        'class="btn btn-sm btn-outline-secondary ms-2" '
        'data-action="translate-resource" '
        f'data-resource-id="{getattr(resource, "id", "")}">'
        '<i class="bi bi-translate"></i> Translate'
        "</button>"
    )


@register.filter
def startswith(value, prefix):
    """Simple startswith filter for templates."""
    try:
        return str(value).startswith(prefix)
    except Exception:
        return False


def _looks_like_url(url: str) -> bool:
    """
    Heuristic: true URLs start with http(s) or ftp.

    ONIX-derived filenames and bare IDs are deliberately excluded so they
    are not auto-wrapped as external links.
    """
    if not url:
        return False
    return url.lower().startswith(("http://", "https://", "ftp://"))


@register.filter
def normalise_oer_url(url: str) -> str:
    """Normalize known OER repository handles to stable landing-page URLs."""
    if not url:
        return url
    if url.startswith("https://hdl.handle.net/20.500.12657/"):
        return url.replace(
            "https://hdl.handle.net/20.500.12657/",
            "https://library.oapen.org/handle/20.500.12657/",
            1,
        )
    if url.startswith("https://hdl.handle.net/20.500.12854/"):
        return url.replace(
            "https://hdl.handle.net/20.500.12854/",
            "https://directory.doabooks.org/handle/20.500.12854/",
            1,
        )
    return url


@register.filter
def link_type_button(resource):
    """
    Generate appropriate button text and icon based on link type.

    Detects PDFs, web pages, and other formats for librarian-friendly display.
    Only treats values that look like real URLs as external; ONIX-style
    filenames or bare identifiers are left for internal handling.
    """
    if not resource or not hasattr(resource, "url"):
        return mark_safe('<span class="text-muted small">No external link available</span>')

    raw_url = resource.url or ""
    if not _looks_like_url(raw_url):
        # No trustworthy external URL; show neutral text
        return mark_safe(
            '<span class="text-muted small">No external link available</span>'
        )

    # Apply URL normalisation (OAPEN/DOAB handles, etc.)
    url = normalise_oer_url(raw_url)
    url_lower = url.lower()
    format_field = (
        resource.format.lower()
        if hasattr(resource, "format") and resource.format
        else ""
    )

    # Detect PDF downloads
    if ".pdf" in url_lower or "pdf" in format_field or url_lower.endswith(".pdf"):
        icon = "📄"
        text = "Download PDF"
        btn_class = "btn-danger"
        title_attr = "Direct PDF download"

    # Detect EPUB/ebook formats
    elif ".epub" in url_lower or "epub" in format_field:
        icon = "📖"
        text = "Download E-book"
        btn_class = "btn-info"
        title_attr = "E-book format (EPUB)"

    # Detect video content
    elif any(
        vid in url_lower or vid in format_field
        for vid in ["youtube.com", "vimeo.com", "video", ".mp4", ".webm"]
    ):
        icon = "🎬"
        text = "View Video"
        btn_class = "btn-dark"
        title_attr = "Video resource"

    # Detect DOI links (scholarly articles)
    elif "doi.org" in url_lower or "dx.doi.org" in url_lower:
        icon = "🔗"
        text = "View Article (DOI)"
        btn_class = "btn-success"
        title_attr = "Academic article via DOI"

    # Detect archive.org links
    elif "archive.org" in url_lower:
        icon = "📚"
        text = "View on Archive.org"
        btn_class = "btn-warning"
        title_attr = "Internet Archive resource"

    # Detect repository/institutional pages
    elif any(
        repo in url_lower for repo in ["repository", "oer", "dspace", "eprints", "oapen", "doab"]
    ):
        icon = "🗃️"
        text = "View in Repository"
        btn_class = "btn-primary"
        title_attr = "Institutional repository"

    # Default: web page
    else:
        icon = "🌐"
        text = "View Resource"
        btn_class = "btn-outline-primary"
        title_attr = "External web page"

    return mark_safe(
        f'<a href="{url}" '
        f'class="btn btn-sm {btn_class}" '
        f'title="{title_attr}" '
        'target="_blank" rel="noopener">'
        f'{icon} {text}</a>'
    )
