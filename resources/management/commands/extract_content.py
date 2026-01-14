from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q
from resources.models import OERResource
from resources.tasks import fetch_and_extract_content
from tqdm import tqdm
from typing import Any


class Command(BaseCommand):
    help = "Fetch and extract content for resources (async via Celery)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--resource-id',
            type=int,
            help='ID of single resource to process'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all resources'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of resources to process'
        )
        parser.add_argument(
            '--source',
            type=str,
            default=None,
            help='Only process resources from specific source name'
        )
        parser.add_argument(
            '--pdf-only',
            action='store_true',
            help='Only extract from PDF URLs'
        )
        parser.add_argument(
            '--ready-only',
            action='store_true',
            help='Only extract for resources ready for review'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-extract even if content already exists'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without enqueueing'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # Single resource mode
        rid = options.get('resource_id')
        if rid:
            fetch_and_extract_content.delay(rid)
            msg = f'✓ Enqueued extraction for resource {rid}'
            self.stdout.write(self.style.SUCCESS(msg))
            return

        # Build query - always start with QuerySet
        qs = OERResource.objects.all()
        
        # Apply filters
        if options['ready_only']:
            qs = qs.filter(readiness_for_review=True)
            self.stdout.write("Filter: Ready for review only")
        
        if not options['force']:
            # Only process resources without extracted text
            qs = qs.filter(
                Q(extracted_text__isnull=True) | Q(extracted_text='')
            )
            self.stdout.write("Filter: Missing extracted_text")
        
        source_name = options.get('source')
        if source_name:
            qs = qs.filter(source__name=source_name)
            self.stdout.write(f"Filter: Source = {source_name}")
        
        if options['pdf_only']:
            qs = qs.filter(url__icontains='.pdf')
            self.stdout.write("Filter: PDF URLs only")
        
        # Filter out invalid URLs
        qs = qs.exclude(url__isnull=True).exclude(url='')
        
        # Get total before limiting
        total = qs.count()
        
        # Apply limit for actual processing
        limit = options.get('limit')
        if limit:
            qs = qs[:limit]
            total = min(total, limit)
        
        header = "\n📥 Content Extraction Queue"
        self.stdout.write(self.style.SUCCESS(header))
        self.stdout.write(f"Resources to process: {total}")
        
        if total == 0:
            self.stdout.write(self.style.WARNING("No resources match criteria"))
            return
        
        # Dry run mode
        if options['dry_run']:
            warning = "\n[DRY RUN - No tasks will be enqueued]"
            self.stdout.write(self.style.WARNING(warning))
            
            # Use list() to convert QuerySet slice
            samples = list(qs[:10])
            for resource in samples:
                url_type = 'PDF' if '.pdf' in resource.url.lower() else 'HTML'
                title = resource.title[:60] if len(resource.title) > 60 else resource.title
                line = f"  [{url_type}] {title}... ({resource.source.name})"
                self.stdout.write(line)
            
            if total > 10:
                self.stdout.write(f"  ... and {total - 10} more")
            return
        
        # Enqueue tasks
        self.stdout.write("\n⏳ Enqueueing Celery tasks...")
        count = 0
        
        # Use iterator() properly - it's a QuerySet method
        with tqdm(total=total, desc="Enqueueing") as pbar:
            for resource in qs.iterator(chunk_size=100):
                # Explicitly type hint for Pylance
                resource_id: int = resource.pk  # Use pk instead of id
                fetch_and_extract_content.delay(resource_id)
                count += 1
                pbar.update(1)
        
        success_msg = f'\n✓ Enqueued {count} extraction tasks'
        self.stdout.write(self.style.SUCCESS(success_msg))
        
        self.stdout.write("\nℹ️  Monitor Celery worker logs for progress")
        check_msg = "   Check: docker-compose logs -f celery_worker"
        self.stdout.write(check_msg)
