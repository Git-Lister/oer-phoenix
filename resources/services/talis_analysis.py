# resources/services/talis_analysis.py

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from resources.services.search_engine import OERSearchEngine, SearchResult
from resources.services.talis import TalisItem, TalisList

logger = logging.getLogger(__name__)


@dataclass
class TalisItemAnalysis:
    item: TalisItem
    results: List[SearchResult] = field(default_factory=list)
    coverage_label: str = "unknown"


@dataclass
class TalisAnalysisSummary:
    total_items: int
    items_with_matches: int
    coverage_percentage: float
    breakdown_by_type: Dict[str, int]


@dataclass
class TalisAnalysisResult:
    talis_list: TalisList
    item_analyses: List[TalisItemAnalysis]
    summary: TalisAnalysisSummary


def _build_query(item: TalisItem) -> str:
    bits = [item.title]
    if item.authors:
        bits.append(item.authors)
    if item.isbn:
        bits.append(f"ISBN {item.isbn}")
    if item.doi:
        bits.append(f"DOI {item.doi}")
    if item.publisher:
        bits.append(f"Publisher {item.publisher}")
    if item.publication_year:
        bits.append(item.publication_year)
    return " ".join(bits)


def _label_coverage(results: List[SearchResult]) -> str:
    if not results:
        return "none"
    top = max(results, key=lambda r: r.final_score)
    if top.final_score >= 0.8:
        return "good"
    if top.final_score >= 0.5:
        return "partial"
    return "weak"


def analyse_talis_list(talis_list: TalisList, limit: int = 5) -> TalisAnalysisResult:
    engine = OERSearchEngine()
    item_analyses: List[TalisItemAnalysis] = []
    breakdown_by_type: Dict[str, int] = {}

    total_items = len(talis_list.items)
    for idx, item in enumerate(talis_list.items, 1):
        logger.info(f"Analysing item {idx}/{total_items}: {item.title}")
        
        query = _build_query(item)
        results = []
        
        try:
            results = engine.hybrid_search(query, limit=limit)
        except Exception as e:
            logger.warning(
                f"Hybrid search failed for item {idx} ({item.title}). Error: {e}. "
                f"Continuing with no results for this item."
            )
            results = []

        for r in results:
            r_type = getattr(r.resource, "resource_type", "unknown")
            breakdown_by_type[r_type] = breakdown_by_type.get(r_type, 0) + 1

        label = _label_coverage(results)
        item_analyses.append(
            TalisItemAnalysis(item=item, results=results, coverage_label=label)
        )

    total = len(talis_list.items)
    with_matches = sum(1 for ia in item_analyses if ia.results)
    coverage_pct = (with_matches / total * 100.0) if total else 0.0

    summary = TalisAnalysisSummary(
        total_items=total,
        items_with_matches=with_matches,
        coverage_percentage=coverage_pct,
        breakdown_by_type=breakdown_by_type,
    )
    return TalisAnalysisResult(
        talis_list=talis_list,
        item_analyses=item_analyses,
        summary=summary,
    )
