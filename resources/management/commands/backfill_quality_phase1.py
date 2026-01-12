from django.core.management.base import BaseCommand
from resources.models import OERResource
from resources.quality import update_quality_fields


class Command(BaseCommand):
    help = "Backfill Phase 1 quality fields (metadata readiness + trust signals)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit to N resources (for testing)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options.get("limit")
        
        qs = OERResource.objects.all()
        if limit:
            qs = qs[:limit]
        
        total = qs.count()
        self.stdout.write(f"Processing {total} resources...")
        
        ready_count = 0
        by_completeness = {
            "high": 0,    # >= 0.8
            "medium": 0,  # >= 0.5
            "low": 0,     # < 0.5
        }
        
        for obj in qs.iterator(chunk_size=500):
            result = update_quality_fields(obj, save=not dry_run)
            
            score = result['readiness']['score']
            if score >= 0.8:
                by_completeness['high'] += 1
            elif score >= 0.5:
                by_completeness['medium'] += 1
            else:
                by_completeness['low'] += 1
            
            if result['readiness']['ready']:
                ready_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"\nProcessed {total} resources"))
        self.stdout.write(f"  Ready for AI review: {ready_count} ({ready_count/total*100:.1f}%)")
        self.stdout.write(f"  High completeness (≥80%): {by_completeness['high']}")
        self.stdout.write(f"  Medium completeness (50-79%): {by_completeness['medium']}")
        self.stdout.write(f"  Low completeness (<50%): {by_completeness['low']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run mode: no changes saved"))
