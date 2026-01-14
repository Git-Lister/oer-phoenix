from django.core.management.base import BaseCommand
from django.db.models import Q
from resources.models import OERResource
from resources.quality import update_ai_pedagogy_fields
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Phase 2: Run AI pedagogical assessments on ready resources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of resources to process (for testing)'
        )
        parser.add_argument(
            '--source',
            type=str,
            default=None,
            help='Only process resources from specific source name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without saving'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-assess resources that already have AI reviews'
        )

    def handle(self, *args, **options):
        # Query resources ready for AI review WITH extracted content
        qs = OERResource.objects.filter(
            readiness_for_review=True
        ).exclude(
            extracted_text__isnull=True
        ).exclude(
            extracted_text=''
        ).order_by('-extracted_at')  # Prioritize recently extracted
        
        if not options['force']:
            # Only process resources without existing AI assessment
            qs = qs.filter(
                Q(ai_pedagogy_scores={}) | Q(ai_pedagogy_scores__isnull=True)
            )
        
        if options['source']:
            qs = qs.filter(source__name=options['source'])
        
        if options['limit']:
            qs = qs[:options['limit']]

        total = qs.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nPhase 2: AI Pedagogical Assessment"
            )
        )
        self.stdout.write(f"Resources to assess: {total}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN - No changes will be saved]"))
            for resource in qs[:10]:  # Show first 10
                self.stdout.write(f"  - {resource.title[:60]}...")
            return
        
        # Process resources
        processed = 0
        failed = 0
        
        with tqdm(total=total, desc="Assessing resources") as pbar:
            for resource in qs.iterator():
                try:
                    assessment = update_ai_pedagogy_fields(resource, save=True)
                    processed += 1
                    
                    # Show sample output
                    if processed <= 3:
                        self.stdout.write(
                            f"\nSample: {resource.title[:50]}"
                        )
                        self.stdout.write(
                            f"  Confidence: {assessment['confidence']}"
                        )
                        self.stdout.write(
                            f"  Summary: {assessment['summary'][:80]}..."
                        )
                    
                except Exception as e:
                    failed += 1
                    if failed <= 5:
                        self.stdout.write(
                            self.style.ERROR(
                                f"\nFailed: {resource.title[:50]}: {str(e)}"
                            )
                        )
                
                pbar.update(1)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Processed: {processed} resources"
            )
        )
        if failed:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Failed: {failed} resources"
                )
            )
        
        # Show statistics
        with_high_confidence = OERResource.objects.filter(
            ai_review_confidence__gte=0.7
        ).count()
        
        self.stdout.write(
            f"\nHigh-confidence assessments (≥0.7): {with_high_confidence}"
        )

