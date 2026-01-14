"""
Unified metadata enrichment for OER resources.
Can be called from management commands or integrated into harvesters.
"""
import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Centralized metadata enrichment logic"""
    
    # Comprehensive stopword list (from clean_metadata_noise.py)
    NOISE_SUBJECTS = {
        'the', 'this', 'these', 'that', 'those', 'there', 'here',
        'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
        'from', 'of', 'as', 'while', 'few', 'some', 'many', 'all',
        'most', 'it', 'they', 'we', 'you', 'he', 'she',
        # German
        'die', 'der', 'das', 'dem', 'den', 'des', 'ein', 'eine',
        'einer', 'einem', 'eines', 'und', 'oder', 'aber', 'auch',
        'im', 'in', 'zu', 'zur', 'zum', 'von', 'vom', 'bei',
        # French  
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du',
        'et', 'ou', 'dans', 'pour', 'sur', 'avec', 'sans',
    }
    
    LICENSE_PATTERNS = [
        (r'cc[\\s-]?by[\\s-]?nc[\\s-]?nd', 'CC BY-NC-ND'),
        (r'cc[\\s-]?by[\\s-]?nc[\\s-]?sa', 'CC BY-NC-SA'),
        (r'cc[\\s-]?by[\\s-]?nc', 'CC BY-NC'),
        (r'cc[\\s-]?by[\\s-]?nd', 'CC BY-ND'),
        (r'cc[\\s-]?by[\\s-]?sa', 'CC BY-SA'),
        (r'cc[\\s-]?by', 'CC BY'),
        (r'cc0|creative commons zero', 'CC0'),
        (r'public domain', 'Public Domain'),
    ]
    
    SUBJECT_KEYWORDS = {
        'Mathematics': ['mathematics', 'math', 'calculus', 'algebra', 'geometry', 'statistics'],
        'Biology': ['biology', 'biological', 'life science', 'ecology', 'genetics'],
        'Chemistry': ['chemistry', 'chemical', 'organic', 'inorganic'],
        'Physics': ['physics', 'physical', 'mechanics', 'thermodynamics'],
        'Computer Science': ['programming', 'computing', 'software', 'algorithm', 'python', 'java'],
        'History': ['history', 'historical', 'ancient', 'medieval'],
        'Literature': ['literature', 'poetry', 'novel', 'fiction', 'drama'],
        'Economics': ['economics', 'economic', 'finance', 'business', 'accounting'],
        'Health Sciences': ['health', 'medicine', 'medical', 'nursing', 'clinical'],
        'Engineering': ['engineering', 'mechanical', 'electrical', 'civil'],
        'Education': ['education', 'teaching', 'pedagogy', 'learning'],
        'Psychology': ['psychology', 'psychological', 'cognitive', 'behavioral'],
        'Sociology': ['sociology', 'social', 'society', 'culture'],
        'Environmental Science': ['environmental', 'environment', 'climate', 'sustainability'],
        'Political Science': ['politics', 'political', 'government', 'democracy'],
        'Philosophy': ['philosophy', 'philosophical', 'ethics', 'logic'],
        'Art & Design': ['art', 'design', 'drawing', 'painting', 'visual'],
        'Music': ['music', 'musical', 'composition', 'performance'],
    }
    
    def enrich_resource(self, resource) -> Dict[str, Any]:
        """
        Enrich a single resource with all available metadata improvements.
        Returns dict of changes made.
        """
        changes = {}
        
        # 1. Extract/clean subject
        if not resource.subject:
            subject = self._extract_subject(resource)
            if subject:
                resource.subject = subject
                changes['subject'] = f'extracted: {subject}'
        else:
            cleaned = self._clean_subject(resource.subject)
            if cleaned != resource.subject:
                resource.subject = cleaned
                changes['subject'] = f'cleaned: {cleaned}'
        
        # 2. Extract/clean license
        if not resource.license and resource.description:
            license_info = self._extract_license(resource.description)
            if license_info:
                resource.license = license_info
                changes['license'] = license_info
        
        # 3. Enhance short descriptions
        if resource.description and len(resource.description) < 50:
            enhanced = self._enhance_description(resource)
            if enhanced and len(enhanced) >= 50:
                resource.description = enhanced
                changes['description'] = f'enhanced ({len(enhanced)} chars)'
        
        # 4. Clean author/publisher fields
        if resource.author:
            cleaned_author = self._clean_text_field(resource.author)
            if cleaned_author != resource.author:
                resource.author = cleaned_author
                changes['author'] = 'cleaned'
        
        if resource.publisher:
            cleaned_pub = self._clean_text_field(resource.publisher)
            if cleaned_pub != resource.publisher:
                resource.publisher = cleaned_pub
                changes['publisher'] = 'cleaned'
        
        return changes
    
    def _extract_subject(self, resource) -> str:
        """Extract subject from description or title"""
        # Try description first
        if resource.description:
            subject = self._extract_from_description(resource.description)
            if subject:
                return subject
        
        # Try title
        if resource.title:
            subject = self._infer_from_title(resource.title)
            if subject:
                return subject
        
        return ""
    
    def _extract_from_description(self, text: str) -> str:
        """Extract subject from description text"""
        patterns = [
            r"(?:focuses? on|covers?|explores?|examines?|about)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+){0,2})",
            r"in\\s+([A-Z][a-z]+\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                subject = match.group(1).strip()
                first_word = subject.split()[0].lower()
                if first_word not in self.NOISE_SUBJECTS and len(subject) > 4:
                    return subject
        
        # Fallback: capitalized phrases
        caps = re.findall(r'\\b([A-Z][a-z]+\\s+[A-Z][a-z]+)\\b', text[:300])
        for phrase in caps:
            first_word = phrase.split()[0].lower()
            if first_word not in self.NOISE_SUBJECTS:
                return phrase
        
        return ""
    
    def _infer_from_title(self, title: str) -> str:
        """Infer subject from title keywords"""
        title_lower = title.lower()
        
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return subject
        
        return ""
    
    def _clean_subject(self, subject: str) -> str:
        """Remove stopwords and noise from subject field"""
        # Split on common delimiters
        parts = re.split(r'[;,|]', subject)
        cleaned_parts = []
        
        for part in parts:
            part = part.strip()
            first_word = part.split()[0].lower() if part else ""
            
            # Skip if starts with stopword or too short
            if first_word not in self.NOISE_SUBJECTS and len(part) > 3:
                cleaned_parts.append(part)
        
        return '; '.join(cleaned_parts[:3])  # Keep top 3 subjects
    
    def _extract_license(self, text: str) -> str:
        """Extract license from text"""
        text_lower = text.lower()
        
        for pattern, license_name in self.LICENSE_PATTERNS:
            if re.search(pattern, text_lower):
                return license_name
        
        return ""
    
    def _enhance_description(self, resource) -> str:
        """Combine short description with other metadata"""
        parts = [resource.description] if resource.description else []
        
        if hasattr(resource, 'coverage_notes') and resource.coverage_notes:
            parts.append(resource.coverage_notes)
        
        if resource.publisher and len(' '.join(parts)) < 50:
            parts.append(f"Published by {resource.publisher}")
        
        if resource.subject and len(' '.join(parts)) < 50:
            parts.insert(0, f"{resource.subject}:")
        
        combined = '. '.join(p.strip() for p in parts if p)
        return combined if len(combined) >= 50 else ""
    
    def _clean_text_field(self, text: str) -> str:
        """Clean text field of common issues"""
        if not text:
            return text
        
        # Remove excess whitespace
        text = ' '.join(text.split())
        
        # Remove common prefixes
        prefixes = ['by ', 'By ', 'from ', 'From ']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]
        
        return text.strip()
