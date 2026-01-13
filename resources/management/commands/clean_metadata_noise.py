"""
Comprehensive metadata noise cleanup - subjects, descriptions, licenses.
Handles multilingual stopwords and common data quality issues.
"""
from django.core.management.base import BaseCommand
from resources.models import OERResource
from collections import Counter
import re


class Command(BaseCommand):
    help = "Clean noise from subject, description, and other metadata fields"

    # Comprehensive stopword list (English + common European languages)
    NOISE_SUBJECTS = {
        # English articles/pronouns/prepositions
        'the', 'this', 'these', 'that', 'those', 'there', 'here',
        'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
        'from', 'of', 'as', 'while', 'few', 'some', 'many', 'all',
        'most', 'it', 'they', 'we', 'you', 'he', 'she',
        
        # German articles/pronouns
        'die', 'der', 'das', 'dem', 'den', 'des', 'ein', 'eine',
        'einer', 'einem', 'eines', 'und', 'oder', 'aber', 'auch',
        'im', 'in', 'zu', 'zur', 'zum', 'von', 'vom', 'bei',
        
        # French articles/pronouns
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de',
        'et', 'ou', 'mais', 'dans', 'sur', 'avec', 'pour',
        
        # Spanish articles/pronouns
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'y', 'o', 'pero', 'en', 'con', 'por', 'para', 'de',
        
        # Dutch articles/pronouns
        'de', 'het', 'een', 'en', 'of', 'maar', 'ook', 'in',
        'op', 'van', 'voor', 'naar', 'met', 'bij',
        
        # Generic/placeholder subjects
        'introduction', 'overview', 'preface', 'foreword',
        'chapter', 'section', 'part', 'volume', 'issue',
        'n/a', 'na', 'none', 'unknown', 'unspecified',
        'other', 'miscellaneous', 'various', 'general',
    }
    
    # License patterns that shouldn't be in subjects
    LICENSE_PATTERNS = [
        r'creative commons.*',
        r'cc[\s-]?(by|nc|nd|sa|zero|0).*',
        r'public domain',
        r'open access',
        r'gnu.*',
        r'mit license',
        r'apache.*',
        r'copyright.*',
    ]

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--report-only", action="store_true", 
                          help="Just show what would be cleaned")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        report_only = options["report_only"]
        
        self.stdout.write(self.style.WARNING("\n=== METADATA NOISE AUDIT ===\n"))
        
        # 1. Analyze current noise
        self._analyze_noise()
        
        if report_only:
            return
        
        # 2. Clean subjects
        cleaned_subjects = self._clean_subjects(dry_run)
        
        # 3. Clean descriptions (remove empty/too short)
        cleaned_descriptions = self._clean_descriptions(dry_run)
        
        # 4. Verify license field separation
        moved_licenses = self._verify_license_separation(dry_run)
        
        # 5. Clean author field (remove URLs/emails mistakenly placed there)
        cleaned_authors = self._clean_authors(dry_run)
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n=== CLEANUP COMPLETE ==="))
        self.stdout.write(f"Subjects cleaned: {cleaned_subjects}")
        self.stdout.write(f"Descriptions cleaned: {cleaned_descriptions}")
        self.stdout.write(f"Licenses relocated: {moved_licenses}")
        self.stdout.write(f"Authors cleaned: {cleaned_authors}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: no changes saved"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Re-run backfill_quality_phase1 to update scores"))

    def _analyze_noise(self):
        """Analyze and report current noise levels."""
        self.stdout.write("\n1. Subject Field Analysis:")
        
        # Count subjects
        all_subjects = OERResource.objects.exclude(subject='').values_list('subject', flat=True)
        total_with_subjects = all_subjects.count()
        
        # Find noise subjects
        noise_count = 0
        noise_examples = []
        
        for subj in all_subjects[:1000]:  # Sample 1000
            first_word = subj.split(',')[0].strip().lower()
            if first_word in self.NOISE_SUBJECTS:
                noise_count += 1
                if len(noise_examples) < 10:
                    noise_examples.append(subj)
        
        estimated_noise = int((noise_count / 1000) * total_with_subjects)
        
        self.stdout.write(f"  Total with subjects: {total_with_subjects}")
        self.stdout.write(f"  Estimated noise: ~{estimated_noise} ({noise_count/10:.1f}%)")
        if noise_examples:
            self.stdout.write(f"  Examples: {', '.join(noise_examples[:5])}")
        
        # Check for license-in-subject
        license_in_subject = OERResource.objects.filter(
            subject__iregex=r'(creative commons|cc by|public domain)'
        ).count()
        self.stdout.write(f"  Licenses in subject field: {license_in_subject}")
        
        # Description quality
        self.stdout.write("\n2. Description Field Analysis:")
        empty_desc = OERResource.objects.filter(description='').count()
        short_desc = OERResource.objects.exclude(description='').filter(
            description__regex=r'^.{1,49}$'
        ).count()
        self.stdout.write(f"  Empty descriptions: {empty_desc}")
        self.stdout.write(f"  Too short (<50 chars): {short_desc}")
        
        # Author field noise
        self.stdout.write("\n3. Author Field Analysis:")
        urls_in_author = OERResource.objects.filter(author__icontains='http').count()
        emails_in_author = OERResource.objects.filter(author__icontains='@').count()
        self.stdout.write(f"  URLs in author field: {urls_in_author}")
        self.stdout.write(f"  Emails in author field: {emails_in_author}")

    def _clean_subjects(self, dry_run):
        """Remove noise subjects."""
        self.stdout.write("\n4. Cleaning subjects...")
        
        qs = OERResource.objects.exclude(subject='')
        cleaned = 0
        
        for obj in qs.iterator(chunk_size=500):
            original = obj.subject
            
            # Split on comma, clean each part
            parts = [p.strip() for p in obj.subject.split(',')]
            clean_parts = []
            
            for part in parts:
                first_word = part.split()[0].lower() if part else ''
                
                # Skip if noise word
                if first_word in self.NOISE_SUBJECTS:
                    continue
                
                # Skip if license pattern
                if any(re.match(pat, part.lower()) for pat in self.LICENSE_PATTERNS):
                    continue
                
                # Skip if too short (single letter)
                if len(part) <= 2:
                    continue
                
                clean_parts.append(part)
            
            new_subject = ', '.join(clean_parts[:3])  # Max 3 subjects
            
            if new_subject != original:
                if len(clean_parts) == 0:
                    obj.subject = ''
                else:
                    obj.subject = new_subject
                
                if not dry_run:
                    obj.save(update_fields=['subject'])
                
                cleaned += 1
                if cleaned <= 20:  # Show first 20
                    self.stdout.write(f"  [{obj.id}] '{original}' → '{obj.subject}'")
        
        return cleaned

    def _clean_descriptions(self, dry_run):
        """Remove placeholder descriptions."""
        self.stdout.write("\n5. Cleaning descriptions...")
        
        PLACEHOLDER_PATTERNS = [
            r'^n/a$',
            r'^none$',
            r'^\.+$',
            r'^-+$',
            r'^\s*$',
        ]
        
        qs = OERResource.objects.exclude(description='')
        cleaned = 0
        
        for obj in qs.iterator(chunk_size=500):
            desc_lower = obj.description.lower().strip()
            
            # Check for placeholders
            is_placeholder = any(re.match(pat, desc_lower) for pat in PLACEHOLDER_PATTERNS)
            
            if is_placeholder:
                obj.description = ''
                if not dry_run:
                    obj.save(update_fields=['description'])
                cleaned += 1
        
        return cleaned

    def _verify_license_separation(self, dry_run):
        """Double-check no licenses remain in subjects."""
        moved = 0
        
        qs = OERResource.objects.filter(
            subject__iregex=r'(creative commons|cc by|cc0|public domain)'
        )
        
        for obj in qs.iterator(chunk_size=500):
            # Move to license field if empty
            if not obj.license:
                obj.license = obj.subject
            obj.subject = ''
            
            if not dry_run:
                obj.save(update_fields=['subject', 'license'])
            moved += 1
        
        return moved

    def _clean_authors(self, dry_run):
        """Remove URLs/emails from author field."""
        cleaned = 0
        
        # URLs in author
        qs = OERResource.objects.filter(author__icontains='http')
        for obj in qs.iterator(chunk_size=500):
            obj.author = re.sub(r'https?://\S+', '', obj.author).strip()
            if not dry_run:
                obj.save(update_fields=['author'])
            cleaned += 1
        
        # Emails in author (keep if it's the only identifier)
        qs = OERResource.objects.filter(author__icontains='@')
        for obj in qs.iterator(chunk_size=500):
            # Only remove if there's other text
            if len(obj.author) > 50:  # Has name + email
                obj.author = re.sub(r'\S+@\S+', '', obj.author).strip()
                if not dry_run:
                    obj.save(update_fields=['author'])
                cleaned += 1
        
        return cleaned
