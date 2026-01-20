"""
RAG (Retrieval-Augmented Generation) orchestration service.

This module combines semantic search over OER resources with LLM-based answer generation
to provide users with synthesized, cited answers to their questions about the collection.

Main entry point: answer_with_rag(query: str, k: int = 5) -> dict
"""

import logging
from typing import List, Dict

from resources.models import OERResource
from resources.services.search_engine import OERSearchEngine, SearchResult
from resources.services.ai_utils import get_llm_client

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a helpful assistant for an open educational resource (OER) discovery platform.
Your role is to help users find and understand educational resources in the collection.

Important rules:
1. Only use information from the provided resources to answer the question.
2. If the user's question cannot be answered using the provided resources, clearly say you are not sure.
3. Always cite the resources you use by their ID in square brackets, e.g., [R1234].
4. Be concise and focus on educational value and relevance.
5. If multiple resources are relevant, mention the most useful ones first."""


def build_context(results: List[SearchResult]) -> str:
    """
    Build a context string from search results for the LLM.
    
    Prioritizes extracted text (richer content) → description → title.
    Truncates each resource's content to keep prompt manageable.
    
    Args:
        results: List of SearchResult objects from OERSearchEngine.semantic_search()
    
    Returns:
        Formatted context string with resource metadata and content.
    """
    chunks = []
    for idx, result in enumerate(results, start=1):
        resource = result.resource  # SearchResult wraps OERResource ORM instance
        
        # Priority: extracted_text (rich) → description → title
        content = (
            getattr(resource, 'extracted_text', None) or
            getattr(resource, 'description', '') or
            getattr(resource, 'title', '')
        )
        
        # Truncate to keep context window reasonable
        content = str(content)[:800] if content else "(No content available)"
        
        title = getattr(resource, 'title', 'Untitled')
        rid = getattr(resource, 'id', '?')
        
        chunks.append(
            f"[Resource R{rid}] {title}\n"
            f"Content: {content}\n"
        )
    
    return "\n---\n".join(chunks)


def answer_with_rag(query: str, k: int = 5) -> Dict:
    """
    Generate an LLM-based answer to a query using retrieved OER resources.
    
    This is the main RAG orchestration function:
    1. Retrieve relevant resources via OERSearchEngine.semantic_search()
    2. If no results, return a friendly message without calling the LLM
    3. Build a context string from retrieved resources
    4. Call the configured LLM with the context and query
    5. Return the answer along with resource metadata for citations
    
    Args:
        query: The user's question or search query.
        k: Maximum number of resources to retrieve (default: 5).
    
    Returns:
        dict with keys:
            - "answer": str - The LLM-generated answer or a message if no resources found
            - "resource_ids": list[int] - IDs of resources used to generate the answer
            - "resources": list[dict] - Full metadata for cited resources
    """
    
    # Step 1: Retrieve relevant resources
    engine = OERSearchEngine()
    results = engine.semantic_search(query=query, limit=k)
    
    logger.info(f"RAG retrieval for query '{query}': found {len(results)} resources")
    
    # Step 2: Handle no-results case explicitly
    if not results:
        logger.info(f"RAG: No resources found for query '{query}'")
        return {
            "answer": (
                "I couldn't find any relevant resources in the collection for your question. "
                "Please try a different query or browse the resource collection directly."
            ),
            "resource_ids": [],
            "resources": [],
        }
    
    # Step 3: Build context from results
    context = build_context(results)
    
    # Step 4: Call LLM with context and query
    try:
        llm_client = get_llm_client()
        
        # Construct the full prompt
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"---\n\n"
            f"USER QUESTION:\n{query}\n\n"
            f"---\n\n"
            f"RELEVANT RESOURCES:\n{context}\n\n"
            f"---\n\n"
            f"ANSWER:\n"
        )
        
        # Invoke the LLM (LangChain API: returns string directly)
        answer_text = llm_client.invoke(prompt)
        
        # Ensure we have a string
        if not isinstance(answer_text, str):
            answer_text = str(answer_text)
        
        logger.info(f"RAG: Generated answer for query '{query}' ({len(answer_text)} chars)")
        
    except Exception as e:
        logger.error(f"RAG: LLM invocation failed for query '{query}': {e}", exc_info=True)
        answer_text = (
            f"I encountered an error while generating an answer. "
            f"The system returned: {str(e)}"
        )
    
    # Step 5: Build response with resource metadata for client-side citations
    resource_metadata = []
    for result in results:
        resource = result.resource
        resource_metadata.append({
            "id": getattr(resource, 'id', None),
            "title": getattr(resource, 'title', ''),
            "url": getattr(resource, 'url', ''),
            "source": resource.source.get_display_name() if getattr(resource, 'source', None) else '',
            "relevance_pct": result.relevance_pct,  # Normalized 0-100 user-facing score
        })
    
    return {
        "answer": answer_text,
        "resource_ids": [r.resource.id for r in results],
        "resources": resource_metadata,
    }


def parse_citations(answer_text: str, resource_ids: list) -> str:
    """
    Parse [R123] citations in answer text and convert to HTML anchor links.
    
    Converts citations like [R123] to <a href="#resource-123" class="citation-link">[R123]</a>
    only if the resource ID is in the provided resource_ids list.
    
    Args:
        answer_text: The answer text containing [R###] citations
        resource_ids: List of valid resource IDs (from the resources list)
    
    Returns:
        HTML string with citations converted to anchor links
    """
    import re
    
    if not answer_text or not resource_ids:
        return answer_text
    
    # Convert resource_ids to set for O(1) lookup
    valid_ids = set(int(rid) if isinstance(rid, str) else rid for rid in resource_ids)
    
    def replace_citation(match):
        """Replace [R123] with anchor link if ID is in valid_ids"""
        citation_text = match.group(0)  # e.g., "[R123]"
        try:
            # Extract the ID from [R123]
            rid_str = citation_text[2:-1]  # Remove [R and ]
            rid = int(rid_str)
            
            if rid in valid_ids:
                return f'<a href="#resource-{rid}" class="citation-link" title="View cited resource">{citation_text}</a>'
        except (ValueError, IndexError):
            pass
        
        # If not valid, return as-is
        return citation_text
    
    # Find all [R###] patterns and replace valid ones
    result = re.sub(r'\[R\d+\]', replace_citation, answer_text)
    return result
