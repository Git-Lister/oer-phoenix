"""
Management command: Backfill descriptions from URLs for resources with boilerplate descriptions.

This command identifies OERResources that have weak/boilerplate descriptions but valid URLs,
then enqueues background tasks to fetch and extract better descriptions from those URLs.

Useful after large KBART harvests that only provide generic descriptions.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from resources.models import OERResource
from resources.tasks import enrich_description_from_url
from resources.utils.description_utils import is_boilerplate_description


class Command(BaseCommand):
    help = "Enqueue description enrichment tasks for resources with boilerplate descriptions and a URL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of resources to process (None = unlimited)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=20,
            help="Number of Celery tasks to enqueue per batch",
        )
        parser.add_argument(
            "--source-id",
            type=int,
            default=None,
            help="Restrict to a specific OERSource ID (useful for focusing on KBART sources)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show counts and candidates, do not enqueue tasks",
        )

    def handle(self, *args, **options):
        # Build queryset: resources with URLs
        qs = OERResource.objects.filter(url__isnull=False).exclude(url="").select_related("source")
        
        # Optional: filter by source
        if options["source_id"] is not None:
            qs = qs.filter(source_id=options["source_id"])
            source = OERResource.objects.filter(source_id=options["source_id"]).first()
            if source and source.source:
                self.stdout.write(f"Filtering by source: {source.source.get_display_name()}")
        
        total_count = qs.count()
        self.stdout.write(f"Checking {total_count} resources with URLs...")

        # Identify candidates: those with boilerplate descriptions
        candidates = []
        for r in qs.iterator():
            if is_boilerplate_description(r.description):
                candidates.append(r.id)

        # Apply limit if specified
        if options["limit"]:
            candidates = candidates[: options["limit"]]

        self.stdout.write(f"\nFound {len(candidates)} resources needing enrichment:")
        if not candidates:
            self.stdout.write(self.style.SUCCESS("No resources need enrichment at this time."))
            return

        # Show sample of candidates
        for rid in candidates[:5]:
            resource = OERResource.objects.get(id=rid)
            self.stdout.write(
                f"  - {resource.id}: {resource.title[:60]}"
                f"\n    Source: {resource.source.get_display_name() if resource.source else 'Unknown'}"
                f"\n    Current desc: {(resource.description or 'EMPTY')[:80]}"
            )
        if len(candidates) > 5:
            self.stdout.write(f"  ... and {len(candidates) - 5} more")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("\n[DRY RUN] Not enqueueing tasks. Use without --dry-run to process.")
            )
            return

        # Enqueue tasks
        self.stdout.write("\nEnqueueing tasks...")
        batch_size = options["batch_size"]
        total_enqueued = 0
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i : i + batch_size]
            for rid in batch:
                enrich_description_from_url.delay(rid)
                total_enqueued += 1
            self.stdout.write(f"  Enqueued batch {(i // batch_size) + 1} ({len(batch)} tasks)")

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Successfully enqueued {total_enqueued} description enrichment tasks!")
        )
        self.stdout.write("Tasks will run in background. Monitor Celery worker logs for progress.")
