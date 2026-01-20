from celery import shared_task
from .services.oer_api import fetch_oer_resources
from .services.talis import TalisClient
from .models import OERResource
from .services import ai_utils
from celery.utils.log import get_task_logger
from django.utils import timezone
import requests
from .models import TalisPushJob
from .services import content_extractor
from .services import metadata_enricher


logger = get_task_logger(__name__)

def get_resource_embedding(description, title):
    # Example implementation (replace with actual logic)
    return f"{description} {title}"

@shared_task(bind=True, max_retries=3)
def fetch_oer_resources_task(self):
    try:
        # Fetch new OER resources from all active sources
        fetch_oer_resources()
        return "Harvest completed successfully"
    except Exception as e:
        # Retry the task after 30 seconds
        raise self.retry(countdown=30, exc=e)

def generate_embeddings():
    """Generate embeddings for all resources without them"""
    # Filter resources where content_embedding is null
    resources = OERResource.objects.filter(content_embedding__isnull=True)
    
    # Generate embeddings in batches
    for resource in resources:
        embedding = get_resource_embedding(resource.description, resource.title)
        resource.content_embedding = embedding
        resource.save()


@shared_task(bind=True, max_retries=3)
def generate_embedding_for_resource(self, resource_id):
    """Celery task to compute an embedding for a single resource by id."""
    try:
        success = ai_utils.compute_and_store_embedding_for_resource(resource_id)
        return success
    except Exception as e:
        raise self.retry(countdown=30, exc=e)


@shared_task(bind=True, max_retries=3)
def fetch_and_extract_content(self, resource_id):
    """Download the resource URL, extract text (PDF or HTML), save to model, and trigger enrichment."""
    try:
        resource = OERResource.objects.get(id=resource_id)
    except OERResource.DoesNotExist:
        logger.error("Resource %s not found", resource_id)
        return False

    url = getattr(resource, 'url', None)
    if not url:
        logger.info("Resource %s has no URL to fetch", resource_id)
        return False

    try:
        result = content_extractor.fetch_and_extract(url)
    except Exception as e:
        # Be defensive: treat HTTP 404 as terminal regardless of exception type
        resp = getattr(e, 'response', None)
        status = None
        try:
            status = resp.status_code if resp is not None else None
        except Exception:
            status = None

        message = str(e) or ''
        if status == 404 or '404' in message:
            logger.warning("Resource %s returned 404; marking as unavailable and skipping retries", resource_id)
            resource.extracted_text = ''
            resource.content_hash = f'HTTP/404'
            resource.content_source_type = 'other'
            resource.extracted_at = timezone.now()
            resource.save(update_fields=['extracted_text', 'content_hash', 'content_source_type', 'extracted_at'])
            return True

        logger.exception("Failed to fetch/extract content for %s: %s", resource_id, e)
        # Retry for other errors
        raise self.retry(countdown=60, exc=e)

    content_hash = result.get('content_hash')
    # Skip if unchanged
    if content_hash and resource.content_hash == content_hash and resource.extracted_text:
        logger.info("Resource %s content unchanged (hash match), skipping", resource_id)
        return True

    text = result.get('text') or ''
    source_type = result.get('source_type') or ''

    # Save extracted text and metadata
    resource.extracted_text = text[:200000] if text else ''
    resource.content_hash = content_hash or ''
    resource.content_source_type = source_type
    resource.extracted_at = timezone.now()
    resource.save(update_fields=['extracted_text', 'content_hash', 'content_source_type', 'extracted_at'])

    # Trigger enrichment using extracted text
    try:
        metadata_enricher.enrich_resource_with_extracted_text(resource, text)
    except Exception:
        logger.exception('Enrichment after extraction failed for resource %s', resource_id)

    return True

@shared_task
def export_to_talis(resource_ids, title, description):
    """
    Celery task to export resources to Talis Reading List
    """
    client = TalisClient()
    resources = OERResource.objects.filter(id__in=resource_ids)
    list_id = client.create_reading_list(title, description, resources)
    return f"Successfully created Talis reading list: {list_id}"


@shared_task(bind=True)
def talis_push_report(self, push_job_id):
    """Task: post stored report snapshot to configured Talis API and update job."""
    try:
        job = TalisPushJob.objects.get(id=push_job_id)
    except TalisPushJob.DoesNotExist:
        logger.error(f"TalisPushJob {push_job_id} not found")
        return False

    job.status = 'running'
    job.started_at = timezone.now()
    job.save()

    talis_url = job.target_url
    if not talis_url:
        logger.error(f"TalisPushJob {job.id} missing target_url, aborting push.")
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.response_body = 'Missing Talis API endpoint.'
        job.save()
        return False

    # If token is stored in settings (not on job), fetch from settings
    from django.conf import settings
    talis_token = getattr(settings, 'TALIS_API_TOKEN', None)

    # Build CSV payload
    import csv
    from io import StringIO

    s = StringIO()
    writer = csv.writer(s)
    writer.writerow(['Original Title', 'Original Author', 'Matched Resource ID', 'Matched Title', 'Matched URL', 'Score', 'Source'])
    for item in job.report_snapshot:
        orig = item.get('original', {})
        matches = item.get('matches', [])
        if not matches:
            writer.writerow([orig.get('title', ''), orig.get('author', ''), '', '', '', '', ''])
        else:
            for m in matches:
                writer.writerow([orig.get('title', ''), orig.get('author', ''), m.get('id'), m.get('title'), m.get('url'), m.get('final_score'), m.get('source')])

    payload = s.getvalue().encode('utf-8')
    headers = {'Content-Type': 'text/csv'}
    if talis_token:
        headers['Authorization'] = f'Bearer {talis_token}'

    try:
        resp = requests.post(talis_url, data=payload, headers=headers, timeout=60)
        job.response_code = getattr(resp, 'status_code', None)
        try:
            job.response_body = resp.text
        except Exception:
            job.response_body = ''

        if resp.status_code in (200, 201):
            job.status = 'completed'
        else:
            job.status = 'failed'

    except Exception as e:
        logger.exception('Error pushing to Talis')
        job.status = 'failed'
        job.response_body = str(e)

    job.completed_at = timezone.now()
    job.save()
    return job.status


# =====================================================================
# Description Enrichment
# =====================================================================

@shared_task(bind=True, max_retries=3)
def enrich_description_from_url(self, resource_id: int):
    """
    Fetch a better description from a resource's URL when current description is boilerplate/empty.
    
    Strategy:
    1. Check if resource has a URL
    2. Check if current description is boilerplate/weak
    3. Fetch URL and extract metadata (meta description, OG tags, or first paragraph)
    4. Update resource if better description found
    5. Track enrichment timestamp
    
    Args:
        resource_id: ID of OERResource to enrich
    """
    from resources.utils.description_utils import is_boilerplate_description, extract_description_from_html
    
    try:
        resource = OERResource.objects.get(id=resource_id)
    except OERResource.DoesNotExist:
        logger.warning("Resource %s not found for description enrichment", resource_id)
        return False
    
    if not resource.url:
        logger.debug("Resource %s has no URL, skipping enrichment", resource_id)
        return False
    
    # If description is already meaningful, skip
    if not is_boilerplate_description(resource.description):
        logger.debug("Resource %s already has meaningful description, skipping", resource_id)
        return False
    
    # Try to fetch the URL and extract better description
    try:
        resp = requests.get(resource.url, timeout=10)
        if resp.status_code != 200:
            logger.info("Enrichment for %s failed: HTTP %s", resource_id, resp.status_code)
            return False
    except requests.Timeout:
        logger.info("Enrichment for %s failed: timeout", resource_id)
        return False
    except Exception as e:
        logger.info("Enrichment for %s failed: %s", resource_id, type(e).__name__)
        return False
    
    # Extract description from HTML
    desc = extract_description_from_html(resp.text)
    
    if not desc:
        logger.debug("Could not extract description for resource %s", resource_id)
        return False
    
    # Update resource and track enrichment
    resource.description = desc
    resource.description_last_enriched_at = timezone.now()
    resource.save(update_fields=["description", "description_last_enriched_at"])
    
    logger.info("Enriched description for resource %s (%d chars)", resource_id, len(desc))
    return True