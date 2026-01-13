"""
Phase 1: Evidence-based quality indicators for OER resources.
Focuses on objective metadata completeness and transparent trust signals.
NO subjective media-type weighting.
"""
from django.utils import timezone


def compute_readiness_score(obj) -> dict:
    """
    Calculate metadata completeness (0-1) - purely factual check.
    Adjusted for realistic OER metadata: license often unspecified.
    """
    # Core required fields (always checked)
    checks = {
        'has_title': bool(obj.title and len(obj.title) > 10),
        'has_description': bool(obj.description and len(obj.description) > 50),
        'has_url': bool(obj.url),
        'has_subject': bool(obj.subject),
    }
    
    # Bonus fields (nice to have, but not blockers)
    bonus_checks = {
        'has_license': bool(obj.license),
        'has_author_or_publisher': bool(obj.author or obj.publisher),
    }
    
    # Core score: 4 required fields
    core_score = sum(checks.values()) / len(checks)
    
    # Bonus score: 2 optional fields
    bonus_score = sum(bonus_checks.values()) / len(bonus_checks)
    
    # Final score: 70% core + 30% bonus
    score = (0.7 * core_score) + (0.3 * bonus_score)
    
    # Ready if: 3 out of 4 core fields (75% of core) OR final score ≥ 70%
    ready = (sum(checks.values()) >= 3) or (score >= 0.7)  # CHANGED
    
    # Missing field list (only show core fields)
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


def compute_ai_pedagogical_assessment(obj) -> dict:
    """
    Phase 2: AI pedagogical quality assessment.
    
    Evaluates teaching utility using LLM analysis of:
    - Learning objectives clarity
    - Pedagogical structure
    - Practice/assessment opportunities
    - Instructor guidance
    - Accessibility considerations
    
    Returns:
        dict with 'scores' (0-5 scale), 'summary' (text), 'confidence' (0-1)
    """
    from resources.services.ai_utils import get_llm_client
    import json
    
    # Build context from resource metadata and content
    context = f"""
Title: {obj.title}
Description: {obj.description[:500] if obj.description else 'N/A'}
Resource Type: {obj.normalised_type or obj.resource_type}
Subject: {obj.subject}
Level: {obj.level if obj.level else 'Not specified'}
Author/Publisher: {obj.author or obj.publisher or 'Unknown'}
License: {obj.license}
"""
    
    # Add extracted content if available (truncate for token limits)
    if obj.extracted_text:
        context += f"\n\nContent Sample:\n{obj.extracted_text[:2000]}..."
    
    # Calculate confidence based on available data
    confidence_factors = {
        'has_description': bool(obj.description and len(obj.description) > 100),
        'has_extracted_content': bool(obj.extracted_text),
        'has_subject': bool(obj.subject),
        'has_level': bool(obj.level),
    }
    confidence = sum(confidence_factors.values()) / len(confidence_factors)
    
    # If confidence too low, return early with placeholder
    if confidence < 0.4:
        return {
            'scores': {},
            'summary': 'Insufficient metadata for pedagogical assessment',
            'confidence': confidence
        }
    
    # Construct LLM prompt
    prompt = f"""You are an educational content quality assessor. Analyze this Open Educational Resource for teaching utility.

{context}

Evaluate the resource on these pedagogical dimensions (0-5 scale):

1. **learning_objectives_clarity**: Are learning goals clear and measurable?
2. **pedagogical_structure**: Is content well-organized for learning?
3. **practice_opportunities**: Does it include exercises, activities, or assessments?
4. **instructor_guidance**: Are there teaching notes or guidance for educators?
5. **accessibility**: Is there evidence of accessibility considerations?

Provide your assessment as JSON:
{{
  "learning_objectives_clarity": <score 0-5>,
  "pedagogical_structure": <score 0-5>,
  "practice_opportunities": <score 0-5>,
  "instructor_guidance": <score 0-5>,
  "accessibility": <score 0-5>,
  "summary": "<2-3 sentence teaching utility summary>"
}}

Base scores on evidence in the metadata/content. Use lower scores when information is unavailable."""

    response = None  # Initialize to fix "possibly unbound" warning
    
    try:
        llm = get_llm_client()
        response = llm.invoke(prompt)
        
        # Handle different response types - ensure we always have a string
        if isinstance(response, list):
            # If it's a list, join it or take first element
            response_text: str = str(' '.join(str(item) for item in response))
        elif isinstance(response, dict):
            # If it's already a dict, use it directly
            response_text = str(json.dumps(response))
        else:
            # Assume it's a string
            response_text = str(response)
        
        # Parse JSON from response
        # Handle potential markdown code blocks
        response_text = response_text.strip()
        if '```json' in response_text:
            # Extract content between ```json and ```
            parts = response_text.split('```json')
            if len(parts) > 1:
                inner_parts = parts[1].split('```')
                response_text = str(inner_parts if len(inner_parts) > 0 else response_text)
        elif '```' in response_text:
            parts = response_text.split('```')
            if len(parts) > 2:
                response_text = str(parts)[1]
            elif len(parts) > 1:
                response_text = str(parts)[1]
        
        # Try to find JSON in the response
        # Look for the first { and last }
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            response_text = response_text[start_idx:end_idx+1]
        
        result = json.loads(response_text.strip())
        
        # Extract scores and summary
        scores = {k: v for k, v in result.items() if k != 'summary'}
        summary = result.get('summary', '')
        
        return {
            'scores': scores,
            'summary': summary,
            'confidence': round(confidence, 2)
        }
        
    except json.JSONDecodeError as e:
        # Log the problematic response for debugging
        response_preview = str(response)[:200] if response is not None else 'No response'
        return {
            'scores': {},
            'summary': f'JSON parse error: {str(e)[:100]}. Response preview: {response_preview}',
            'confidence': 0.0
        }
    except Exception as e:
        # Fallback on error
        response_preview = str(response)[:100] if response is not None else 'No response'
        return {
            'scores': {},
            'summary': f'Assessment failed: {str(e)[:100]} | Response: {response_preview}',
            'confidence': 0.0
        }


def update_ai_pedagogy_fields(obj, save=False):
    """
    Update Phase 2 AI pedagogy fields on a resource.
    
    Args:
        obj: OERResource instance
        save: If True, saves the object after updating
    """
    assessment = compute_ai_pedagogical_assessment(obj)
    
    obj.ai_pedagogy_scores = assessment['scores']
    obj.ai_review_summary = assessment['summary']
    obj.ai_review_confidence = assessment['confidence']
    
    if save:
        obj.save(update_fields=[
            'ai_pedagogy_scores',
            'ai_review_summary',
            'ai_review_confidence'
        ])
    
    return assessment
