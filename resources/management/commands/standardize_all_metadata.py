"""
Master command to standardize ALL metadata in database.
Runs enrichment + quality calculation in one pass.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from resources.models import OERResource
from resources.services.metadata_enrichment import MetadataEnricher
from resources.quality import update_quality_fields
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Standardize metadata for all resources in database'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, help='Limit to N resources')
        parser.add_argument(
            '--source',
            type=str,
            help='Only process specific source'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-process all resources (not just incomplete)'
        )

    def handle(self, *args, **options):
        enricher = MetadataEnricher()
        
        # Query strategy
        if options['force']:
            qs = OERResource.objects.all()
        else:
            # Target resources needing enrichment
            qs = OERResource.objects.filter(
                Q(subject='') | Q(subject__isnull=True) |
                Q(license='') | Q(license__isnull=True) |
                Q(metadata_quality_score__lt=0.7)
            )
        
        if options['source']:
            qs = qs.filter(source__name=options['source'])
        
        if options['limit']:
            qs = qs[:options['limit']]
        
        total = qs.count()
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🔧 Standardizing Metadata")
        )
        self.stdout.write(f"Resources to process: {total:,}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN]"))
        
        enriched_count = 0
        improved_quality = 0
        
        with tqdm(total=total, desc="Processing") as pbar:
            for resource in qs.iterator(chunk_size=500):
                old_score = resource.metadata_quality_score
                
                # Enrich metadata
                changes = enricher.enrich_resource(resource)
                
                if changes:
                    enriched_count += 1
                    
                    if not options['dry_run']:
                        resource.save()
                    
                    # Show samples
                    if enriched_count <= 5:
                        self.stdout.write(f"\n[{resource.id}] {resource.title[:50]}")
                        for field, change in changes.items():
                            self.stdout.write(f"   {field}: {change}")
                
                # Update quality scores
                if not options['dry_run']:
                    update_quality_fields(resource, save=True)
                    
                    if old_score < 0.7 and resource.metadata_quality_score >= 0.7:
                        improved_quality += 1
                
                pbar.update(1)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Processed: {total:,} resources"
            )
        )
        self.stdout.write(f"  Enriched: {enriched_count:,}")
        self.stdout.write(f"  Quality improved (→≥70%): {improved_quality:,}")
        
        if not options['dry_run']:
            # Final stats
            ready = OERResource.objects.filter(readiness_for_review=True).count()
            total_resources = OERResource.objects.count()
            
            self.stdout.write(
                f"\n📊 Database Status:"
            )
            self.stdout.write(
                f"  Ready for Phase 2: {ready:,}/{total_resources:,} "
                f"({ready/total_resources*100:.1f}%)"
            )
