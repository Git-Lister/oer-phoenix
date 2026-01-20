"""
Enhanced OER Search Engine
Unified search system with semantic + keyword hybrid search,
quality-based ranking, and filtering capabilities
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import numpy as np
from django.db.models import Q, QuerySet, Count

from resources.models import OERResource
from resources.services.ai_utils import get_embedding_model

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Structured search result with scoring.
    
    Fields:
    - resource: OERResource ORM instance
    - similarity_score: Raw similarity (0.0 - 1.0)
    - quality_score: Internal quality metric (0.0 - 1.0, from 0-5 scale)
    - final_score: Combined score for ranking (similarity + quality boost)
    - relevance_pct: Normalized user-facing score (0-100%, derived from similarity)
    - match_reason: "semantic", "keyword", or "hybrid"
    """
    resource: OERResource
    similarity_score: float = 0.0
    quality_score: float = 0.0
    quality_boost: float = 0.0
    final_score: float = 0.0
    relevance_pct: int = 0  # 0-100, rounded; THIS is the user-facing score
    match_reason: str = ""


class OERSearchEngine:
    """
    Unified search engine for OER resources,
    using semantic similarity, keyword matching, and quality metrics.
    """

    def __init__(self) -> None:
        self.embedding_model = get_embedding_model()
        self.similarity_threshold = 0.45
        self.quality_weight = 0.3
        self.keyword_weight = 0.7

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_resource_quality_score(self, resource: OERResource) -> float:
        """Get quality score for a resource."""
        score = getattr(resource, "overall_quality_score", None)
        if score is not None:
            return float(score)

        if hasattr(resource, "quality_scores"):
            val = resource.quality_scores.get("overall", 0.0)
            return float(val) if val else 0.0

        return 0.0

    def _cosine_similarity(self, a: Any, b: Any) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr = np.array(a, dtype=float)
        b_arr = np.array(b, dtype=float)

        if np.linalg.norm(a_arr) == 0 or np.linalg.norm(b_arr) == 0:
            return 0.0

        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    # ------------------------------------------------------------------
    # Core search operations
    # ------------------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
        include_inactive: bool = False,
    ) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        try:
            logger.info("AI Search (semantic): %s", query)
            query_embedding = self.embedding_model.encode([query])[0]

            qs: QuerySet[OERResource] = OERResource.objects.select_related("source").all()
            if not include_inactive:
                qs = qs.filter(is_active=True)

            # Apply filters first to reduce candidates
            if filters:
                qs = self._apply_filters(qs, filters)

            candidates = [r for r in qs if getattr(r, "content_embedding", None) is not None]
            logger.info("AI Search: %d resources with embeddings", len(candidates))

            results: List[SearchResult] = []
            for res in candidates:
                emb = res.content_embedding
                if not isinstance(emb, (list, np.ndarray)):
                    emb = list(emb) if hasattr(emb, "tolist") else emb

                try:
                    sim = self._cosine_similarity(query_embedding, emb)
                except Exception as e:
                    logger.warning("Cosine similarity error for resource %s: %s", getattr(res, "id", "?"), e)
                    sim = 0.0

                # Quality score (0-1, derived from internal 0-5 metric)
                quality_score = self._get_resource_quality_score(res) / 5.0
                quality_boost = quality_score * self.quality_weight
                
                # Final ranking score: similarity + quality boost
                final = sim + quality_boost
                
                # Normalized relevance percentage (0-100) for user display
                relevance_pct = int(round(sim * 100))

                results.append(
                    SearchResult(
                        resource=res,
                        similarity_score=sim,
                        quality_score=quality_score,
                        quality_boost=quality_boost,
                        final_score=final,
                        relevance_pct=relevance_pct,
                        match_reason="semantic",
                    )
                )

            results.sort(key=lambda x: x.final_score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error("Semantic search error: %s", e)
            return []

    def _keyword_search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Perform keyword-based search."""
        qs: QuerySet[OERResource] = OERResource.objects.select_related("source").filter(is_active=True)

        if filters:
            qs = self._apply_filters(qs, filters)

        keywords = query.lower().split()
        qobj = Q()

        for kw in keywords:
            qobj |= (
                Q(title__icontains=kw)
                | Q(description__icontains=kw)
                | Q(keywords__icontains=kw)
                | Q(subject__icontains=kw)
            )

        qs = qs.filter(qobj).distinct()

        results: List[SearchResult] = []
        for res in qs[:limit]:
            title_text = (res.title or "").lower()
            desc_text = (res.description or "").lower()

            title_hits = sum(1 for kw in keywords if kw in title_text)
            desc_hits = sum(1 for kw in keywords if kw in desc_text)
            score = (title_hits * 0.6 + desc_hits * 0.4) / max(1, len(keywords))

            # Quality score (0-1, derived from internal 0-5 metric)
            quality_score = self._get_resource_quality_score(res) / 5.0
            quality_boost = quality_score * self.quality_weight
            final = score * self.keyword_weight + quality_boost
            
            # Normalized relevance percentage (0-100) for user display
            relevance_pct = int(round(score * 100))

            results.append(
                SearchResult(
                    resource=res,
                    similarity_score=score,
                    quality_score=quality_score,
                    quality_boost=quality_boost,
                    final_score=final,
                    relevance_pct=relevance_pct,
                    match_reason="keyword",
                )
            )

        return results

    def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Combine semantic and keyword search."""
        semantic_hits = self.semantic_search(query, filters, limit)
        keyword_hits = self._keyword_search(query, filters, limit)

        # Deduplicate and merge
        merged: Dict[Any, SearchResult] = {}
        for entry in (semantic_hits + keyword_hits):
            rid = getattr(entry.resource, "id", None)
            if rid in merged:
                # Keep higher score, update match reason
                if entry.final_score > merged[rid].final_score:
                    merged[rid] = entry
                merged[rid].match_reason = "hybrid"
            else:
                merged[rid] = entry

        sorted_results = sorted(merged.values(), key=lambda x: x.final_score, reverse=True)
        return sorted_results[:limit]

    # ------------------------------------------------------------------
    # Filtering, faceting, sorting
    # ------------------------------------------------------------------

    def _apply_filters(self, qs: QuerySet, filters: Dict) -> QuerySet:
        """Apply multiple filters to queryset."""
        # Language filter
        if "language" in filters and filters["language"]:
            langs = filters["language"] if isinstance(filters["language"], list) else [filters["language"]]
            qs = qs.filter(language__in=langs)

        # Source filter
        if "source" in filters and filters["source"]:
            sources = filters["source"] if isinstance(filters["source"], list) else [filters["source"]]
            qs = qs.filter(source__id__in=sources)

        # Resource type filter
        if "resource_type" in filters and filters["resource_type"]:
            types = filters["resource_type"] if isinstance(filters["resource_type"], list) else [filters["resource_type"]]
            qs = qs.filter(normalised_type__in=types)


        # Subject filter
        if "subject" in filters and filters["subject"]:
            subjects = filters["subject"] if isinstance(filters["subject"], list) else [filters["subject"]]
            qs = qs.filter(primary_subject__in=subjects)

        # Educational level filter
        if "level" in filters and filters["level"]:
            qs = qs.filter(level__iexact=filters["level"])

        # License filter
        if "license" in filters and filters["license"]:
            qs = qs.filter(license__icontains=filters["license"])

        # Identifier filters
        if "isbn" in filters and filters["isbn"]:
            isbns = filters["isbn"] if isinstance(filters["isbn"], list) else [filters["isbn"]]
            qs = qs.filter(isbn__in=isbns)
        if "issn" in filters and filters["issn"]:
            issns = filters["issn"] if isinstance(filters["issn"], list) else [filters["issn"]]
            qs = qs.filter(issn__in=issns)
        if "oclc_number" in filters and filters["oclc_number"]:
            oclcs = filters["oclc_number"] if isinstance(filters["oclc_number"], list) else [filters["oclc_number"]]
            qs = qs.filter(oclc_number__in=oclcs)

        # Minimum quality filter
        if "min_quality" in filters:
            qs = qs.filter(overall_quality_score__gte=filters["min_quality"])

        return qs


    def get_facets(self, query: Optional[str] = None, applied_filters: Optional[Dict] = None) -> Dict:
        """
        Get facets for filtering with counts.
        If applied_filters provided, return facets based on filtered results.
        """
        qs: QuerySet[OERResource] = OERResource.objects.filter(is_active=True)

        # Apply existing filters to get relevant facets
        if applied_filters:
            qs = self._apply_filters(qs, applied_filters)

        facets = {
            "subjects": list(
                qs.exclude(primary_subject="")
                .values("primary_subject")
                .annotate(count=Count("id"))
                .order_by("-count")[:20]
            ),
            "languages": list(
                qs.exclude(language="")
                .values("language")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "resource_types": list(
                qs.exclude(normalised_type="")
                .values("normalised_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "sources": list(
                qs.values("source__id", "source__name", "source__display_name")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "licenses": list(
                qs.exclude(license="")
                .values("license")
                .annotate(count=Count("id"))
                .order_by("-count")[:15]
            ),
        }

        return facets

    def sort_results(self, results: List[SearchResult], sort_by: str = "relevance") -> List[SearchResult]:
        """Sort search results by different criteria."""
        if sort_by == "newest":
            return sorted(results, key=lambda x: x.resource.created_at or "", reverse=True)
        if sort_by == "quality":
            return sorted(results, key=lambda x: getattr(x.resource, "overall_quality_score", 0.0) or 0.0, reverse=True)
        if sort_by == "title":
            return sorted(results, key=lambda x: (x.resource.title or "").lower())

        # relevance (default)
        return sorted(results, key=lambda x: x.final_score, reverse=True)
