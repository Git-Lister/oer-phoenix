"""
Lightweight content extractor utilities.
- Fetch URL (with size limit)
- Detect content type
- Extract text from HTML (BeautifulSoup) and PDF (pypdf)

Optional: replace or augment with Apache Tika server if available.
"""
import hashlib
import logging
import time
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Configurable limits
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
REQUEST_TIMEOUT = 60  # increased from 20s to handle slow PDF servers (handle.net, OAPEN)
THROTTLE_SECONDS = 1.0  # minimum seconds between requests to same host (per-process)

# Session with retries/backoff
_SESSION = None
_LAST_REQUEST_PER_HOST = {}


def _get_session():
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(['GET', 'POST'])
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        _SESSION = session
    return _SESSION


def _compute_hash(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


def fetch_url_bytes(url: str, timeout: int = REQUEST_TIMEOUT) -> bytes:
    session = _get_session()
    # Simple per-host throttle (note: per-process only)
    host = urlparse(url).netloc
    last = _LAST_REQUEST_PER_HOST.get(host)
    if last:
        elapsed = time.time() - last
        if elapsed < THROTTLE_SECONDS:
            time.sleep(THROTTLE_SECONDS - elapsed)

    resp = session.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    _LAST_REQUEST_PER_HOST[host] = time.time()
    chunks = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Download exceeds max allowed size ({MAX_DOWNLOAD_BYTES} bytes)")
        chunks.append(chunk)
    return b"".join(chunks)


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove scripts/styles
    for s in soup(['script', 'style', 'noscript']):
        s.extract()
    # Prefer main/article if present
    main = soup.find(['main', 'article'])
    text_root = main if main is not None else soup
    texts = [t.strip() for t in text_root.stripped_strings]
    return "\n\n".join(texts)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        logger.exception('pypdf not available; install pypdf to extract PDF text')
        raise

    bio = BytesIO(pdf_bytes)
    reader = PdfReader(bio)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or '')
        except Exception:
            parts.append('')
    return "\n\n".join(p for p in parts if p)


def fetch_and_extract(url: str) -> dict:
    """
    Fetch a URL and attempt to extract normalized text. Returns dict:
    {"text": str, "content_hash": str, "source_type": 'html'|'pdf'|'other'}
    """
    b = fetch_url_bytes(url)
    content_hash = _compute_hash(b)

    # Try to detect PDF by header
    if b.startswith(b"%PDF"):
        text = extract_text_from_pdf_bytes(b)
        return {"text": text, "content_hash": content_hash, "source_type": "pdf"}

    # Otherwise try as HTML
    try:
        html = b.decode('utf-8', errors='ignore')
        text = extract_text_from_html(html)
        return {"text": text, "content_hash": content_hash, "source_type": "html"}
    except Exception:
        return {"text": "", "content_hash": content_hash, "source_type": "other"}
