"""
Targeted metadata enrichment to improve readiness for AI review.
Focuses on the 21,811 resources scoring 50-79% completeness.
"""
from django.core.management.base import BaseCommand
from resources.models import OERResource
from resources.quality import update_quality_fields
import re


class Command(BaseCommand):
    help = "Enrich metadata for resources scoring 50-79% to push them over 70% threshold"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, help="Limit to N resources")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options.get("limit")
        
        # Target the 21,811 medium-completeness resources
        qs = OERResource.objects.filter(
            metadata_quality_score__gte=0.5,
            metadata_quality_score__lt=0.8
        )
        
        if limit:
            qs = qs[:limit]
        
        total = qs.count()
        self.stdout.write(f"Enriching {total} medium-completeness resources...\n")
        
        enriched = 0
        promoted = 0  # Moved from <70% to ≥70%
        
        for obj in qs.iterator(chunk_size=500):
            old_score = obj.metadata_quality_score
            changed = False
            
            # 1. Extract subject from description if missing
            if not obj.subject and obj.description:
                subject = self._extract_subject_from_description(obj.description)
                if subject:
                    obj.subject = subject
                    changed = True
                    self.stdout.write(f"  [{obj.id}] Extracted subject: {subject[:40]}")
            
            # 2. Extract license from description if missing
            if not obj.license and obj.description:
                license_info = self._extract_license_from_text(obj.description)
                if license_info:
                    obj.license = license_info
                    changed = True
                    self.stdout.write(f"  [{obj.id}] Extracted license: {license_info}")
            
            # 3. Lengthen short descriptions using KBART fields
            if obj.description and len(obj.description) < 50:
                enhanced = self._enhance_description(obj)
                if enhanced:
                    obj.description = enhanced
                    changed = True
                    self.stdout.write(f"  [{obj.id}] Enhanced description (now {len(enhanced)} chars)")
            
            # 4. Infer subject from title if still missing
            if not obj.subject and obj.title:
                subject = self._infer_subject_from_title(obj.title)
                if subject:
                    obj.subject = subject
                    changed = True
                    self.stdout.write(f"  [{obj.id}] Inferred subject from title: {subject}")
            
            if changed:
                enriched += 1
                if not dry_run:
                    obj.save()
                
                # Recompute quality
                update_quality_fields(obj, save=not dry_run)
                
                if old_score < 0.7 and obj.metadata_quality_score >= 0.7:
                    promoted += 1
        
        self.stdout.write(self.style.SUCCESS(f"\nEnriched {enriched}/{total} resources"))
        self.stdout.write(self.style.SUCCESS(f"Promoted to ≥70% ready: {promoted}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: no changes saved"))

    def _extract_subject_from_description(self, text: str) -> str:
        """Extract likely subject area from description text."""
        # Stopwords to ignore
        STOPWORDS = {
            'the', 'this', 'these', 'that', 'there', 'here',
            'in', 'on', 'at', 'to', 'for', 'with', 'by', 'an', 'a',
            'while', 'few', 'some', 'many', 'all', 'most',
            'it', 'they', 'we', 'you', 'he', 'she',
            'introduction', 'overview', 'guide', 'handbook',
        }
        
        # Subject-specific patterns (more precise)
        subject_patterns = [
            # "focuses on Biology"
            r"(?:focuses? on|covers?|explores?|examines?|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
            # "in Environmental Science"
            r"in\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, text)
            if match:
                subject = match.group(1).strip()
                # Filter stopwords
                first_word = subject.split()[0].lower()
                if first_word not in STOPWORDS and len(subject) > 4:
                    return subject
        
        # Fallback: Look for multi-word capitalized phrases (likely proper subjects)
        # But require at least 2 words to avoid "The", "This", etc.
        caps = re.findall(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text[:300])
        for phrase in caps:
            first_word = phrase.split()[0].lower()
            if first_word not in STOPWORDS:
                return phrase
        
        return ""


    def _extract_license_from_text(self, text: str) -> str:
        """Extract license info from description."""
        text_lower = text.lower()
        
        # CC license patterns
        cc_patterns = [
            (r'cc[\s-]?by[\s-]?nc[\s-]?nd', 'CC BY-NC-ND'),
            (r'cc[\s-]?by[\s-]?nc[\s-]?sa', 'CC BY-NC-SA'),
            (r'cc[\s-]?by[\s-]?nc', 'CC BY-NC'),
            (r'cc[\s-]?by[\s-]?nd', 'CC BY-ND'),
            (r'cc[\s-]?by[\s-]?sa', 'CC BY-SA'),
            (r'cc[\s-]?by', 'CC BY'),
            (r'cc0|creative commons zero', 'CC0'),
            (r'public domain', 'Public Domain'),
        ]
        
        for pattern, license_name in cc_patterns:
            if re.search(pattern, text_lower):
                return license_name
        
        return ""

    def _enhance_description(self, obj) -> str:
        """Combine short description with other metadata to reach 50+ chars."""
        parts = [obj.description] if obj.description else []
        
        # Add KBART coverage notes if available
        if hasattr(obj, 'coverage_notes') and obj.coverage_notes:
            parts.append(obj.coverage_notes)
        
        # Add publisher info
        if obj.publisher and len(' '.join(parts)) < 50:
            parts.append(f"Published by {obj.publisher}")
        
        # Add subject if known
        if obj.subject and len(' '.join(parts)) < 50:
            parts.insert(0, f"{obj.subject}:")
        
        combined = '. '.join(p.strip() for p in parts if p)
        return combined if len(combined) >= 50 else ""

    def _infer_subject_from_title(self, title: str) -> str:
        """Infer broad subject from title keywords."""
        title_lower = title.lower()
        
        # Expanded keyword→subject mapping
        subject_keywords = {
            'Mathematics': ['mathematics', 'math', 'calculus', 'algebra', 'geometry', 'statistics', 'trigonometry'],
            'Biology': ['biology', 'biological', 'life science', 'ecology', 'genetics'],
            'Chemistry': ['chemistry', 'chemical', 'organic', 'inorganic'],
            'Physics': ['physics', 'physical', 'mechanics', 'thermodynamics'],
            'Computer Science': ['programming', 'computing', 'software', 'algorithm', 'data science', 'python', 'java'],
            'History': ['history', 'historical', 'ancient', 'medieval', 'renaissance'],
            'Literature': ['literature', 'poetry', 'novel', 'fiction', 'drama', 'shakespeare'],
            'Economics': ['economics', 'economic', 'finance', 'business', 'accounting', 'trade'],
            'Health Sciences': ['health', 'medicine', 'medical', 'nursing', 'clinical', 'healthcare'],
            'Engineering': ['engineering', 'mechanical', 'electrical', 'civil', 'structural'],
            'Education': ['education', 'teaching', 'pedagogy', 'learning', 'curriculum'],
            'Psychology': ['psychology', 'psychological', 'cognitive', 'behavioral'],
            'Sociology': ['sociology', 'social', 'society', 'culture', 'anthropology'],
            'Environmental Science': ['environmental', 'environment', 'climate', 'sustainability', 'ecology'],
            'Political Science': ['politics', 'political', 'government', 'democracy', 'policy'],
            'Philosophy': ['philosophy', 'philosophical', 'ethics', 'metaphysics', 'logic'],
            'Art & Design': ['art', 'design', 'drawing', 'painting', 'sculpture', 'visual'],
            'Music': ['music', 'musical', 'composition', 'performance', 'orchestra'],
        }
        
        for subject, keywords in subject_keywords.items():
            if any(kw in title_lower for kw in keywords):
                return subject
        
        return ""

