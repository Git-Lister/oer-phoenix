from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OERResource
from .tasks import generate_embedding_for_resource, fetch_and_extract_content, enrich_description_from_url



@receiver(post_save, sender=OERResource)
def enqueue_embedding_on_save(sender, instance, created, **kwargs):
    """When an OERResource is created or updated, enqueue a task to compute its embedding.

    If `content_embedding` is already present and the instance was not just created,
    we only enqueue if the field is empty (conservative behavior).
    """
    try:
        if created:
            # New resource -> compute embedding
            generate_embedding_for_resource.delay(instance.id)
            # Also enqueue content extraction if URL present
            try:
                url = getattr(instance, 'url', None)
                if url:
                    fetch_and_extract_content.delay(instance.id)
            except Exception:
                pass
        else:
            # Updated resource: compute only if missing embedding
            if not instance.content_embedding:
                generate_embedding_for_resource.delay(instance.id)
            # If resource has a URL but no content_hash, enqueue extraction
            try:
                url = getattr(instance, 'url', None)
                content_hash = getattr(instance, 'content_hash', None)
                if url and not content_hash:
                    fetch_and_extract_content.delay(instance.id)
            except Exception:
                pass
    except Exception:
        # Avoid raising from signals
        pass


@receiver(post_save, sender=OERResource)
def enqueue_description_enrichment(sender, instance, created, **kwargs):
    """
    When a new OERResource is created with boilerplate/weak description,
    enqueue description enrichment from its URL.
    
    Skips if:
    - Not a new resource (created=False)
    - No URL available
    - Description is already meaningful
    """
    from resources.utils.description_utils import is_boilerplate_description
    
    try:
        if not created:
            return
        if not instance.url:
            return
        if not is_boilerplate_description(instance.description):
            return
        
        # Enqueue enrichment task
        enrich_description_from_url.delay(instance.id)
    except Exception:
        # Avoid raising from signals
        pass
