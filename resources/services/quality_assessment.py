"""
OER Quality Assessment Service
Automated quality metrics and validation for OER resources
"""

import hashlib
import requests
from typing import Dict, Tuple
from django.utils import timezone
from datetime import timedelta
import logging
from resources.quality import compute_readiness_score, compute_trust_signals


logger = logging.getLogger(__name__)


class QualityAssessmentService:
    """
    Service for assessing OER resource quality across multiple dimensions
    """
    
    def __init__(self):
        self.accessibility_checker_enabled = True  # Can be toggled via settings
        self.url_verification_timeout = 10  # seconds
    
    def assess_resource(self, resource) -> Dict[str, float]:
        """
        Comprehensive quality assessment - Phase 1 evidence-based approach.
        
        Populates:
        - metadata_quality_score (factual completeness)
        - trust_signals (observable indicators)
        - Keeps detailed dimension scores for admin inspection
        
        Returns dict with all scores for logging/display.
        """
        # Phase 1: Compute objective metrics
        readiness = compute_readiness_score(resource)
        trust_signals = compute_trust_signals(resource)
        
        # Store in model fields
        resource.metadata_quality_score = readiness['score']
        resource.readiness_for_review = readiness['ready']
        resource.trust_signals = trust_signals
        
        # Keep detailed checks for admin tools (existing logic)
        detailed_scores = {
            'metadata_completeness': readiness['score'],
            'accessibility_mention': 1.0 if trust_signals['mentions_accessibility'] else 0.0,
            'license_clarity': self.verify_license(resource.license or ""),
            'content_freshness': self.assess_recency(resource.updated_at),
            'url_validity': self.verify_url(resource.url),
        }
        
        # Overall score now represents "data quality" not "pedagogical quality"
        # Average of detailed checks for admin tracking
        overall = sum(detailed_scores.values()) / len(detailed_scores)
        resource.overall_quality_score = round(overall, 2)
        
        return {
            **detailed_scores,
            'overall_score': overall,
            'readiness_score': readiness['score'],
            'ready_for_ai_review': readiness['ready'],
            'trust_signals': trust_signals,
        }


    
    def calculate_metadata_score(self, resource) -> float:
        """
        Assess metadata completeness and quality
        Score: 0.0 to 1.0
        """
        score = 0.0
        total_weight = 0.0
        
        # Required fields (higher weight)
        required_checks = [
            (bool(resource.title and len(resource.title) > 10), 0.15, "title_quality"),
            (bool(resource.description and len(resource.description) > 100), 0.15, "description_quality"),
            (bool(resource.url), 0.10, "url_present"),
            (bool(resource.license), 0.10, "license_present"),
        ]
        
        # Recommended fields (medium weight)
        recommended_checks = [
            (bool(getattr(resource, 'subject', None)), 0.10, "subject"),  # CHANGED
            (bool(getattr(resource, 'level', None)), 0.10, "level"),  # CHANGED
            (bool(resource.publisher), 0.08, "publisher"),
            (bool(getattr(resource, 'author', None)), 0.08, "author"),  # CHANGED
        ]
        
        # Enhanced fields (lower weight)
        enhanced_checks = [
            (bool(getattr(resource, 'keywords', None)), 0.07, "keywords"),  # CHANGED
            (bool(getattr(resource, 'resource_type', None)), 0.05, "resource_type"),  # CHANGED
            (len(resource.description) > 500 if resource.description else False, 0.02, "detailed_description"),
        ]
        
        all_checks = required_checks + recommended_checks + enhanced_checks
        
        for passes_check, weight, field_name in all_checks:
            total_weight += weight
            if passes_check:
                score += weight
        
        return round(score / total_weight if total_weight > 0 else 0, 3)

    
    def check_accessibility_compliance(self, resource) -> float:
        """
        Check accessibility compliance
        Score: 0.0 to 1.0
        
        Note: This is a simplified check. In production, integrate with
        tools like WAVE, Lighthouse, or axe-core for comprehensive testing.
        """
        score = 0.5  # Base score
        
        # Check if URL is accessible
        if resource.last_verified:
            days_since_verified = (timezone.now() - resource.last_verified).days
            if days_since_verified < 30:
                score += 0.2
        
        # Check for accessibility keywords in description
        accessibility_keywords = [
            'wcag', 'accessible', 'screen reader', 'alt text', 
            'closed captions', 'transcript', 'section 508'
        ]
        
        description_lower = resource.description.lower()
        keyword_matches = sum(1 for kw in accessibility_keywords if kw in description_lower)
        score += min(keyword_matches * 0.05, 0.3)
        
        return min(round(score, 3), 1.0)
    
    def verify_license(self, license_str: str) -> float:
        """
        Verify license clarity and openness
        Score: 0.0 to 1.0
        """
        if not license_str:
            return 0.0
        
        license_lower = license_str.lower()
        
        # Creative Commons licenses (best)
        cc_licenses = {
            'cc0': 1.0,  # Most open
            'cc by': 0.95,
            'cc by-sa': 0.90,
            'cc by-nc': 0.75,
            'cc by-nc-sa': 0.70,
            'cc by-nd': 0.60,
            'cc by-nc-nd': 0.50,
        }
        
        for cc_type, score in cc_licenses.items():
            if cc_type in license_lower:
                return score
        
        # Other open licenses
        if any(term in license_lower for term in ['public domain', 'gpl', 'mit', 'apache']):
            return 0.80
        
        # Has some license specified
        if len(license_str) > 5:
            return 0.40
        
        return 0.20  # Unclear license
    
    def assess_recency(self, last_updated) -> float:
        """
        Assess content freshness based on last update
        Score: 0.0 to 1.0
        """
        if not last_updated:
            return 0.5  # Unknown
        
        days_old = (timezone.now() - last_updated).days
        
        if days_old < 180:  # < 6 months
            return 1.0
        elif days_old < 365:  # < 1 year
            return 0.9
        elif days_old < 730:  # < 2 years
            return 0.75
        elif days_old < 1095:  # < 3 years
            return 0.60
        elif days_old < 1825:  # < 5 years
            return 0.40
        else:
            return 0.20  # > 5 years old
    
    def verify_url(self, url: str) -> float:
        """
        Verify URL is accessible and returns valid response
        Score: 0.0 to 1.0
        """
        if not url:
            return 0.0
        
        try:
            response = requests.head(
                url, 
                allow_redirects=True, 
                timeout=self.url_verification_timeout
            )
            
            if response.status_code == 200:
                return 1.0
            elif response.status_code < 400:
                return 0.8  # Redirect or other 2xx/3xx
            elif response.status_code == 404:
                return 0.0  # Not found
            else:
                return 0.3  # Other error
                
        except requests.RequestException as e:
            logger.warning(f"URL verification failed for {url}: {str(e)}")
            return 0.5  # Unknown (network error, timeout, etc.)
    
    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """
        Calculate overall weighted quality score
        Score: 0.0 to 5.0 (for consistency with overall_quality_score)
        """
        weights = {
            'metadata_completeness': 0.25,
            'accessibility': 0.20,
            'license_clarity': 0.20,
            'content_freshness': 0.20,
            'url_validity': 0.15,
        }
        
        weighted_sum = sum(scores.get(key, 0) * weight for key, weight in weights.items())
        
        # Convert to 0-5 scale
        return round(weighted_sum * 5, 2)
    
    def generate_content_hash(self, resource) -> str:
        """
        Generate SHA-256 hash of resource content for version tracking
        """
        content_string = f"{resource.title}|{resource.description}|{resource.url}|{resource.version}"
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    def batch_assess_resources(self, queryset, update_db: bool = True) -> Dict:
        """
        Batch assess multiple resources
        
        Args:
            queryset: QuerySet of OERResource objects
            update_db: Whether to save updated scores to database
            
        Returns:
            Summary statistics
        """
        assessed_count = 0
        improved_count = 0
        total_quality_before = 0
        total_quality_after = 0
        
        for resource in queryset:
            old_score = resource.overall_quality_score
            total_quality_before += old_score
            
            # Perform assessment
            scores = self.assess_resource(resource)
            
            # Update resource
            resource.metadata_quality_score = scores['metadata_completeness']
            resource.accessibility_score = scores['accessibility']
            
            # Recalculate overall score
            resource.update_overall_quality_score()
            
            total_quality_after += resource.overall_quality_score
            
            if resource.overall_quality_score > old_score:
                improved_count += 1
            
            if update_db:
                resource.save()
            
            assessed_count += 1
        
        return {
            'assessed_count': assessed_count,
            'improved_count': improved_count,
            'avg_quality_before': total_quality_before / assessed_count if assessed_count > 0 else 0,
            'avg_quality_after': total_quality_after / assessed_count if assessed_count > 0 else 0,
        }


class AccessibilityChecker:
    """
    Detailed accessibility compliance checking
    Integrate with external tools in production
    """
    
    def check_wcag_compliance(self, url: str, level: str = 'AA') -> Dict:
        """
        Check WCAG compliance level
        
        In production, integrate with:
        - WAVE API: https://wave.webaim.org/api/
        - axe-core: https://github.com/dequelabs/axe-core
        - Lighthouse CI: https://github.com/GoogleChrome/lighthouse-ci
        
        Args:
            url: URL to check
            level: WCAG level ('A', 'AA', or 'AAA')
            
        Returns:
            Dict with compliance details
        """
        # TODO: Implement actual accessibility checking
        # For now, return placeholder
        return {
            'compliant': None,  # Unknown
            'level': level,
            'errors': [],
            'warnings': [],
            'message': 'Accessibility checking not yet implemented'
        }
    
    def check_alt_text_coverage(self, url: str) -> float:
        """
        Check percentage of images with alt text
        """
        # TODO: Implement with actual HTML parsing
        return 0.0


class ContentValidator:
    @staticmethod
    def validate_educational_alignment(resource, course_learning_objectives: list) -> float:
        """
        Check alignment between resource and course learning objectives
        Uses semantic similarity
        """
        from resources.services.ai_utils import get_embedding_model
        import numpy as np
        
        if not resource.learning_objectives or not course_learning_objectives:
            return 0.5  # Unknown
        
        model = get_embedding_model()
        
        def _to_numpy(x):
            """Helper to safely convert tensors or other types to NumPy arrays."""
            if hasattr(x, "cpu"):  # PyTorch tensor
                return x.cpu().numpy()
            elif isinstance(x, list):
                return np.array([_to_numpy(item) for item in x], dtype=np.float32)
            else:
                return np.array(x, dtype=np.float32)
        
        # Get embeddings and convert to NumPy arrays
        resource_embedding = model.encode([resource.learning_objectives])[0]
        resource_embedding = _to_numpy(resource_embedding)
        
        course_embeddings = model.encode(course_learning_objectives)
        course_embeddings = np.stack([_to_numpy(vec) for vec in course_embeddings])
        
        # Calculate maximum similarity across all course objectives
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(
            resource_embedding.reshape(1, -1),
            course_embeddings
        )[0]
        
        return float(np.max(similarities))
    
    @staticmethod
    def check_content_appropriateness(resource) -> Dict:
        """
        Check for inappropriate content, broken links, etc.
        """
        issues = []
        
        # Check for suspicious patterns
        suspicious_keywords = ['buy now', 'limited time', 'trial', 'subscribe']
        description_lower = resource.description.lower()
        
        for keyword in suspicious_keywords:
            if keyword in description_lower:
                issues.append(f"Contains potentially commercial keyword: '{keyword}'")
        
        return {
            'is_appropriate': len(issues) == 0,
            'issues': issues
        }
    