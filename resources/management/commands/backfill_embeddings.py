"""
Management command to backfill embeddings for existing OERResource records.

This command finds all resources without embeddings and enqueues them to the existing
embedding generation Celery task. This is essential for RAG to have reasonable coverage
on existing resource collections before live harvest begins.

Usage:
    python manage.py backfill_embeddings [--limit 100] [--batch-size 10] [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q
from resources.models import OERResource
from resources.tasks import generate_embedding_for_resource
from typing import Any
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Backfill embeddings for OERResource records that are missing them'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of resources to process (default: all)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of Celery tasks to enqueue at a time (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without enqueueing tasks'
        )
        parser.add_argument(
            '--source-id',
            type=int,
            default=None,
            help='Only process resources from a specific source (by ID)'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # Build query for resources without embeddings
        qs = OERResource.objects.filter(
            Q(content_embedding__isnull=True) | Q(content_embedding='')
        ).select_related('source')
        
        # Optional: filter by source
        source_id = options.get('source_id')
        if source_id:
            qs = qs.filter(source_id=source_id)
            self.stdout.write(f"Filter: Source ID = {source_id}")
        
        # Apply limit
        limit = options.get('limit')
        if limit:
            qs = qs[:limit]
            self.stdout.write(f"Limit: {limit} resources")
        
        total = qs.count()
        self.stdout.write(f"Found {total} resources without embeddings")
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No resources to process."))
            return
        
        # Dry run mode
        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING("DRY RUN MODE: Not enqueueing tasks"))
            sample = list(qs[:5])
            for resource in sample:
                self.stdout.write(
                    f"  - {resource.id}: {resource.title[:60]} ({resource.source.get_display_name()})"
                )
            if total > 5:
                self.stdout.write(f"  ... and {total - 5} more")
            return
        
        # Enqueue tasks in batches
        batch_size = options.get('batch_size', 10)
        resource_ids = list(qs.values_list('id', flat=True))
        
        self.stdout.write(f"Enqueueing {total} embedding generation tasks (batch size: {batch_size})...")
        
        with tqdm(total=total, desc="Enqueuing tasks", unit="resource") as pbar:
            for i in range(0, len(resource_ids), batch_size):
                batch = resource_ids[i:i + batch_size]
                for rid in batch:
                    generate_embedding_for_resource.delay(rid)
                    pbar.update(1)
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Successfully enqueued {total} embedding generation tasks to Celery")
        )
        self.stdout.write(
            "Monitor progress with: celery -A oer_rebirth inspect active"
        )
