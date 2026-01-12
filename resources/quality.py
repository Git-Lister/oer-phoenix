"""
Phase 1: Evidence-based quality indicators for OER resources.
Focuses on objective metadata completeness and transparent trust signals.
NO subjective media-type weighting.
"""
from django.utils import timezone


def compute_readiness_score(obj) -> dict:
    """
    Calculate metadata completeness (0-1) - purely factual check.
    Adjusted for realistic OER metadata availability.
    """
    checks = {
        'has_title': bool(obj.title and len(obj.title) > 10),
        'has_description': bool(obj.description and len(obj.description) > 50),  # Lowered from 100
        'has_url': bool(obj.url),
        'has_license': bool(obj.license),
        'has_subject': bool(obj.subject),
        # Removed 'has_level' - rare in OER metadata
        'has_author_or_publisher': bool(obj.author or obj.publisher),
    }
    
    score = sum(checks.values()) / len(checks)
    ready = score >= 0.7  # Still 70% but fewer required fields
    missing = [k.replace('has_', '') for k, v in checks.items() if not v]
    
    return {
        'score': round(score, 2),
        'ready': ready,
        'missing': missing,
    }



def compute_trust_signals(obj) -> dict:
    """
    Generate factual trust indicators - NO hidden weighting.
    Users interpret these themselves.
    
    Returns:
        dict of boolean/string signals to display as badges
    """
    signals = {}
    
    # Curated collection indicator
    CURATED_SOURCES = {
        "MMU-Vetted-OER (Correct Title fields)",
        "OpenStax",
        "OAPEN Library - OAIPMH",
        "DOAB - OAIPMH",
        "Skills Commons OER OAI-PMH",
    }
    signals['from_curated_collection'] = obj.source.name in CURATED_SOURCES
    
    # Peer review indicator (heuristic from description)
    desc_lower = (obj.description or "").lower()
    signals['peer_reviewed'] = any(
        term in desc_lower for term in ['peer-reviewed', 'peer reviewed', 'editorial review']
    )
    
    # Open license clarity
    license_lower = (obj.license or "").lower()
    signals['open_license'] = any(
        cc in license_lower for cc in ['cc by', 'cc0', 'public domain', 'creative commons']
    )
    
    # Recency (within 2 years)
    if obj.updated_at:
        days_old = (timezone.now() - obj.updated_at).days
        signals['updated_recently'] = days_old < 730
    else:
        signals['updated_recently'] = False
    
    # Accessibility mention (NOT compliance, just signal)
    signals['mentions_accessibility'] = any(
        kw in desc_lower for kw in ['wcag', 'accessible', 'screen reader', 'alt text', 'accessibility']
    )
    
    # Has teaching materials (exercises, assessments)
    signals['has_practice_materials'] = any(
        term in desc_lower for term in ['exercises', 'assessment', 'quiz', 'practice', 'activities']
    )
    
    return signals


def update_quality_fields(obj, save=False):
    """
    Convenience function to update all Phase 1 quality fields on a resource.
    
    Args:
        obj: OERResource instance
        save: If True, saves the object after updating
    """
    readiness = compute_readiness_score(obj)
    
    obj.metadata_quality_score = readiness['score']
    obj.readiness_for_review = readiness['ready']
    obj.trust_signals = compute_trust_signals(obj)
    
    if save:
        obj.save(update_fields=[
            'metadata_quality_score',
            'readiness_for_review', 
            'trust_signals'
        ])
    
    return {
        'readiness': readiness,
        'trust_signals': obj.trust_signals,
    }
