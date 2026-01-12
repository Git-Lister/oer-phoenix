from django.core.management.base import BaseCommand
from resources.models import OERResource
import re


class Command(BaseCommand):
    help = "Move license info from subject field to license field"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        
        # License patterns to detect in subject field
        LICENSE_PATTERNS = [
            r'creative commons.*',
            r'cc[\s-]?(by|nc|nd|sa|zero|0).*',
            r'public domain',
            r'open access',
            r'gnu.*license',
            r'mit license',
            r'apache license',
        ]
        
        combined_pattern = '|'.join(f'({p})' for p in LICENSE_PATTERNS)
        regex = re.compile(combined_pattern, re.IGNORECASE)
        
        # Find resources with license-like subjects
        qs = OERResource.objects.exclude(subject='')
        total = qs.count()
        
        moved = 0
        cleared = 0
        
        self.stdout.write(f"Scanning {total} resources for misplaced licenses...\n")
        
        for obj in qs.iterator(chunk_size=500):
            if regex.search(obj.subject):
                license_text = obj.subject.strip()
                
                # If license field is empty or generic, replace it
                if not obj.license or obj.license in ['Unknown', 'Other', '']:
                    obj.license = license_text
                    moved += 1
                    self.stdout.write(f"  [{obj.id}] Moved '{license_text}' to license field")
                else:
                    # License field already has data, just clear subject
                    cleared += 1
                    self.stdout.write(f"  [{obj.id}] Cleared '{license_text}' (license already set)")
                
                # Clear subject field
                obj.subject = ''
                
                if not dry_run:
                    obj.save(update_fields=['subject', 'license'])
        
        self.stdout.write(self.style.SUCCESS(f"\nMoved to license field: {moved}"))
        self.stdout.write(self.style.SUCCESS(f"Cleared (license already set): {cleared}"))
        self.stdout.write(self.style.SUCCESS(f"Total fixed: {moved + cleared}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: no changes saved"))
