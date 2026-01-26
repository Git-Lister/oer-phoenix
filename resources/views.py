# views.py - robust id access emended version

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import Count
from .harvesters.preset_configs import SUPPLIER_PRESETS, PRESET_CONFIGS
import csv
import io
import json
import logging

from .models import OERResource, OERSource, HarvestJob, TalisPushJob
from .forms import (
    CSVUploadForm, ExportForm, APIHarvesterForm, OAIPMHHarvesterForm,
    CSVHarvesterForm, TalisExportForm, HarvesterTypeForm
)
from .forms import KBARTUploadForm, OERSourceForm
from .harvesters.api_harvester import APIHarvester
from .harvesters.oaipmh_harvester import OAIPMHHarvester
from .harvesters.csv_harvester import CSVHarvester
from .harvesters.preset_configs import PresetAPIConfigs, PresetOAIPMHConfigs
from .harvesters.marcxml_harvester import MARCXMLHarvester


# NEW: Talis import/analysis helpers for dashboard workflows
from resources.services.talis import (
    parse_csv_to_talis_list,
    fetch_list_from_url,
    TalisList,
    TalisItem,
)
from resources.services.talis_analysis import analyse_talis_list
from .services.search_engine import OERSearchEngine

logger = logging.getLogger(__name__)


def staff_required(view_func):
    return user_passes_test(lambda u: u.is_staff)(view_func)


# Template path constants for consistency
TEMPLATE_ADMIN_HOME = 'admin/resources/home.html'
TEMPLATE_RESOURCES_HOME = 'resources/home.html'
TEMPLATE_SEARCH = 'resources/search.html'
TEMPLATE_COMPARE = 'resources/compare.html'
TEMPLATE_CSV_UPLOAD = 'admin/resources/csv_upload.html'
TEMPLATE_EXPORT = 'resources/export.html'
TEMPLATE_EXPORT_SUCCESS = 'resources/export_success.html'
TEMPLATE_TALIS_PREVIEW = 'resources/talis_preview.html'
TEMPLATE_BULK_CSV_UPLOAD = 'admin/resources/csv_upload.html'
TEMPLATE_EXPORT_DATA = 'admin/resources/export.html'
TEMPLATE_CREATE_SOURCE = 'admin/resources/create_source.html'
TEMPLATE_ADD_HARVESTER = 'admin/resources/add_harvester.html'
TEMPLATE_OERSOURCE_HARVEST = 'admin/resources/oersource_harvest.html'
TEMPLATE_ADVANCED_SEARCH = "resources/advanced_search.html"


# NEW: session keys for dashboard Talis analysis
TALIS_SESSION_KEY = "dashboard_talis_list"
TALIS_SUMMARY_KEY = "dashboard_talis_summary"
TALIS_ITEMS_KEY = "dashboard_talis_item_analyses"


# ----------------------------------------------------------------------
# NEW: Dashboard + Talis list A/B workflows
# ----------------------------------------------------------------------

def dashboard_view(request):
    """
    Librarian-facing landing page.
    
    Shows:
    - AI search hero (form posts to ai_search).
    - Talis Reading List analysis widget (CSV + URL, posts to talis_list_analyse_view).
    - Quick stats: recent resources, top subjects, resource type breakdown, sources.
    """
    try:
        recent_resources = OERResource.objects.filter(is_active=True).order_by("-created_at")[:10]

        top_subjects = (
            OERResource.objects.filter(is_active=True)
            .exclude(subject="")
            .values("subject")
            .annotate(count=models.Count("id"))
            .order_by("-count")[:15]
        )

        type_counts = (
            OERResource.objects.filter(is_active=True)
            .values("normalised_type")
            .annotate(count=models.Count("id"))
            .order_by("-count")
        )

        chart_labels = []
        chart_data = []
        chart_colors = [
            "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
            "#FF9F40", "#FF6384", "#C9CBCF", "#4BC0C0", "#FF6384",
        ]

        for idx, typeinfo in enumerate(type_counts):
            code = (typeinfo["normalised_type"] or "").strip()
            if not code:
                label = "Unspecified"
            elif code == "book":
                label = "Books"
            elif code == "chapter":
                label = "Chapters"
            elif code == "article":
                label = "Articles"
            elif code == "video":
                label = "Videos"
            elif code == "course":
                label = "Courses"
            else:
                label = "Other"
            chart_labels.append(label)
            chart_data.append(typeinfo["count"])

        # Convert to JSON for JavaScript consumption
        chart_labels_json = json.dumps(chart_labels)
        chart_data_json = json.dumps(chart_data)
        chart_colors_json = json.dumps(chart_colors[: len(chart_data)])

        sources_with_counts = (
            OERSource.objects.filter(is_active=True)
            .annotate(count=models.Count("resources"))
            .order_by("-count")
        )

        stats = {
            "total_resources": OERResource.objects.filter(is_active=True).count(),
            "distinct_subjects": (
                OERResource.objects.filter(is_active=True)
                .exclude(subject="")
                .values("subject")
                .distinct()
                .count()
            ),
            "active_sources": sources_with_counts.count(),
        }

        display_type_counts = []
        for row in type_counts:
            code = (row["normalised_type"] or "").strip()
            if not code:
                label = "(unspecified)"
            elif code == "book":
                label = "Books"
            elif code == "chapter":
                label = "Chapters"
            elif code == "course":
                label = "Courses"
            else:
                label = "Other"
            display_type_counts.append(
                {"code": code or "unspecified", "label": label, "count": row["count"]}
            )

        context = {
            "recent_resources": recent_resources,
            "top_subjects": top_subjects,
            "type_counts": display_type_counts,
            "sources": sources_with_counts,
            "stats": stats,
            "chart_labels": chart_labels_json,
            "chart_data": chart_data_json,
            "chart_colors": chart_colors_json,
        }

        return render(request, "resources/dashboard.html", context)


    except Exception as e:
        logger.error(f"Error in dashboard_view: {str(e)}")
        messages.error(request, "An error occurred while loading the dashboard.")
        return redirect("resources:home")



def talis_list_analyse_view(request):
    """
    Dashboard-initiated Talis list analysis entry:

    - If 'talis_csv' is present in FILES, use CSV workflow (A).
    - Else if 'talis_url' in POST, use URL/API workflow (B).

    Stores a normalised TalisList in session and redirects to preview.
    """
    try:
        if request.method == "POST":
            talis_list = None

            # Basic validation: require either a CSV or a URL
            csv_file = request.FILES.get("dash_talis_csv") or request.FILES.get("talis_csv")
            talis_url = request.POST.get("dash_talis_url", "") or request.POST.get("talis_url", "")
            talis_url = talis_url.strip()

            if not csv_file and not talis_url:
                messages.error(
                    request,
                    "Please upload a Talis CSV file or paste a reading list URL.",
                )
                return redirect("resources:dashboard")

            if csv_file:
                talis_list = parse_csv_to_talis_list(csv_file)
            elif talis_url:
                talis_list = fetch_list_from_url(talis_url)

            if talis_list:
                _store_talis_list_in_session(request, talis_list)
                return redirect("resources:talis_preview_dashboard")

        # GET or invalid POST: show a generic form page (can share template)
        return render(request, "resources/talis_jobs.html", {})
    except Exception as e:
        logger.error(f"Error in talis_list_analyse_view: {str(e)}")
        messages.error(
            request,
            "An error occurred while preparing the Talis analysis.",
        )
        return redirect("resources:dashboard")



def talis_list_preview_view(request):
    """
    Preview of parsed Talis list items before running AI analysis (dashboard flow).
    """
    try:
        talis_list = _load_talis_list_from_session(request)
        if not talis_list:
            messages.warning(request, "No Talis list in session. Please start again.")
            return redirect('resources:talis_analyse_dashboard')

        if request.method == "POST":
            analysis_result = analyse_talis_list(talis_list)
            _store_analysis_in_session(request, analysis_result)
            return redirect('resources:talis_report_dashboard')

        context = {
            "talis_list": talis_list,
            "items": talis_list.items,
        }
        return render(request, "resources/talis_preview.html", context)
    except Exception as e:
        logger.error(f"Error in talis_list_preview_view: {str(e)}")
        messages.error(request, "An error occurred while previewing the Talis list.")
        return redirect('resources:dashboard')


def talis_list_report_view(request):
    """
    OER coverage report for the last analysed Talis list (dashboard flow).
    """
    try:
        talis_list = _load_talis_list_from_session(request)
        if not talis_list:
            messages.warning(request, "No Talis analysis found in session.")
            return redirect('resources:talis_analyse_dashboard')

        summary = request.session.get(TALIS_SUMMARY_KEY)
        item_analyses = request.session.get(TALIS_ITEMS_KEY, [])

        context = {
            "talis_list": talis_list,
            "summary": summary,
            "item_analyses": item_analyses,
        }
        return render(request, "resources/talis_report.html", context)
    except Exception as e:
        logger.error(f"Error in talis_list_report_view: {str(e)}")
        messages.error(request, "An error occurred while loading the Talis report.")
        return redirect('resources:dashboard')


def _store_talis_list_in_session(request, talis_list: TalisList) -> None:
    request.session[TALIS_SESSION_KEY] = {
        "identifier": talis_list.identifier,
        "title": talis_list.title,
        "module_code": talis_list.module_code,
        "academic_year": talis_list.academic_year,
        "source_type": talis_list.source_type,
        "items": [
            {
                "position": i.position,
                "section": i.section,
                "importance": i.importance,
                "item_type": i.item_type,
                "title": i.title,
                "authors": i.authors,
                "isbn": i.isbn,
                "doi": i.doi,
                "url": i.url,
                "notes": i.notes,
            }
            for i in talis_list.items
        ],
    }


def _load_talis_list_from_session(request) -> TalisList | None:
    data = request.session.get(TALIS_SESSION_KEY)
    if not data:
        return None

    items: list[TalisItem] = []
    for row in data.get("items", []):
        items.append(
            TalisItem(
                position=row["position"],
                section=row.get("section"),
                importance=row.get("importance"),
                item_type=row.get("item_type"),
                title=row["title"],
                authors=row.get("authors"),
                isbn=row.get("isbn"),
                doi=row.get("doi"),
                url=row.get("url"),
                notes=row.get("notes"),
            )
        )

    return TalisList(
        identifier=data.get("identifier", "session_list"),
        title=data.get("title"),
        module_code=data.get("module_code"),
        academic_year=data.get("academic_year"),
        source_type=data.get("source_type", "unknown"),
        items=items,
    )


def _store_analysis_in_session(request, analysis_result) -> None:
    # Dashboard summary + analyses
    request.session[TALIS_SUMMARY_KEY] = {
        "total_items": analysis_result.summary.total_items,
        "items_with_matches": analysis_result.summary.items_with_matches,
        "coverage_percentage": analysis_result.summary.coverage_percentage,
        "breakdown_by_type": analysis_result.summary.breakdown_by_type,
    }
    item_analyses_payload = [
        {
            "item": {
                "position": ia.item.position,
                "section": ia.item.section,
                "importance": ia.item.importance,
                "item_type": ia.item.item_type,
                "title": ia.item.title,
                "authors": ia.item.authors,
                "isbn": ia.item.isbn,
                "doi": ia.item.doi,
                "url": ia.item.url,
                "notes": ia.item.notes,
            },
            "coverage_label": ia.coverage_label,
            "results": [
                {
                    "id": getattr(r.resource, "id", None),
                    "title": getattr(r.resource, "title", ""),
                    "url": getattr(r.resource, "url", ""),
                    "final_score": float(r.final_score),
                    "match_reason": r.match_reason,
                    "source": getattr(r.resource.source, "name", ""),
                }
                for r in ia.results
            ],
        }
        for ia in analysis_result.item_analyses
    ]
    request.session[TALIS_ITEMS_KEY] = item_analyses_payload

    # Legacy-style report for talis_report_download
    legacy_report = []
    for entry in item_analyses_payload:
        item = entry["item"]
        matches = entry["results"]
        legacy_report.append({
            "original": {
                "title": item["title"],
                "author": item["authors"],
                "note": item["notes"],
            },
            "matches": matches,
        })
    request.session["talis_report"] = legacy_report



# Search Views
def ai_search(request):
    """
    AI-powered search with:
    - Hybrid (keyword + semantic) ranking via OERSearchEngine
    - Faceted filters (source, language, resource_type, subject)
    - Sort options (relevance, newest, quality, etc.)
    - NEW: RAG mode for LLM-synthesized answers (toggle: rag_mode=1 in POST/GET)
    """
    try:
        # 1. Determine query, sort, and mode
        raw_query = request.POST.get("query", request.GET.get("query", ""))
        query = (raw_query or "").strip()
        sort_by = request.GET.get("sort", "relevance")
        rag_mode = request.POST.get("rag_mode", request.GET.get("rag_mode", "")) == "1"

        # 2. Collect applied filters from GET parameters
        applied_filters = {
            "sources": request.GET.getlist("source"),
            "languages": request.GET.getlist("language"),
            "resource_types": request.GET.getlist("resource_type"),
            "subjects": request.GET.getlist("subject"),
        }

        # Translate applied_filters into engine-friendly filter dict
        search_filters: dict[str, list[str]] = {}
        if applied_filters["sources"]:
            search_filters["source"] = applied_filters["sources"]
        if applied_filters["languages"]:
            search_filters["language"] = applied_filters["languages"]
        if applied_filters["resource_types"]:
            search_filters["resource_type"] = applied_filters["resource_types"]
        if applied_filters["subjects"]:
            search_filters["subject"] = applied_filters["subjects"]

        detailed_results = []
        facets = {}
        rag_answer = ""
        rag_answer_html = ""
        rag_resources = []

        if query:
            from .services.search_engine import OERSearchEngine
            from .services.rag import answer_with_rag, parse_citations

            engine = OERSearchEngine()

            # NEW: RAG mode - generate LLM answer instead of traditional search results
            if rag_mode:
                rag_result = answer_with_rag(query=query, k=5)
                rag_answer = rag_result.get("answer", "")
                rag_answer_html = parse_citations(rag_answer, rag_result.get("resource_ids", []))
                rag_resources = rag_result.get("resources", [])
                
                # For consistency, also retrieve search results to show below
                results = engine.hybrid_search(
                    query=query,
                    filters=search_filters or None,
                    limit=20,
                )
                detailed_results = results
                
                logger.info(f"RAG answer generated for query: {query}")
            else:
                # Traditional search mode
                # 3. Hybrid search with optional filters
                results = engine.hybrid_search(
                    query=query,
                    filters=search_filters or None,
                    limit=50,
                )

                # 4. Apply chosen sort
                results = engine.sort_results(results, sort_by=sort_by)

                # 5. Build facets for sidebar (always pass a dict, no None)
                facets = engine.get_facets(
                    query=query,
                    applied_filters=search_filters,
                )

                detailed_results = results

            # 6. Store light-weight snapshot for Talis/export use
            last_search_results = []
            for r in detailed_results:
                resource = getattr(r, "resource", None)
                source_name = ""
                if resource and getattr(resource, "source", None):
                    source_name = getattr(resource.source, "name", "") or ""

                last_search_results.append(
                    {
                        "id": getattr(resource, "id", None) if resource else None,
                        "title": getattr(resource, "title", "") if resource else "",
                        "url": getattr(resource, "url", "") if resource else "",
                        "final_score": float(getattr(r, "final_score", 0.0)),
                        "source": source_name,
                    }
                )

            request.session["last_search_results"] = last_search_results

        context = {
            "query": query,
            "detailed_results": detailed_results,
            "facets": facets,
            "applied_filters": applied_filters,
            "sort_by": sort_by,
            "ai_search": True,
            "rag_mode": rag_mode,
            "rag_answer": rag_answer,
            "rag_answer_html": rag_answer_html,
            "rag_resources": rag_resources,
        }
        return render(request, TEMPLATE_SEARCH, context)

    except Exception as e:
        logger.error(f"Error in ai_search: {str(e)}")
        messages.error(request, "An error occurred during the search.")
        return render(request, TEMPLATE_ADVANCED_SEARCH, {
            "query": "",
            "detailed_results": [],
            "facets": {},
            "applied_filters": {
                "sources": [], "languages": [], "resource_types": [], "subjects": []
            },
            "sort_by": "relevance",
            "ai_search": True,
            "advanced": True,
        })


def compare_view(request):
    """View for comparing multiple OER resources"""
    try:
        resource_ids = request.session.get('comparison_resources', [])
        resources = OERResource.objects.filter(id__in=resource_ids) if resource_ids else []

        return render(request, TEMPLATE_COMPARE, {
            'resources': resources
        })
    except Exception as e:
        logger.error(f"Error in compare_view: {str(e)}")
        messages.error(request, "An error occurred while loading the comparison view.")
        return redirect('resources:home')

def advanced_search(request):
    """
    Fielded advanced search view.

    - Accepts up to 3 rows of (operator, field, term).
    - Normalises identifier fields (ISBN/ISSN/OCLC) into filters.
    - Uses the same OERSearchEngine.hybrid_search backend as ai_search.
    """
    try:
        # Read fielded rows
        q1 = request.GET.get("q1", "").strip()
        q2 = request.GET.get("q2", "").strip()
        q3 = request.GET.get("q3", "").strip()

        f1 = request.GET.get("f1", "any")
        f2 = request.GET.get("f2", "any")
        f3 = request.GET.get("f3", "any")

        op2 = request.GET.get("op2", "AND")
        op3 = request.GET.get("op3", "AND")

        # Optional extra limits
        adv_resource_type = request.GET.get("adv_resource_type") or ""
        adv_language = request.GET.get("adv_language") or ""

        # Build a human-readable combined query string for display / logging
        parts = []
        if q1:
            parts.append(q1)
        if q2:
            parts.append(f"{op2} {q2}")
        if q3:
            parts.append(f"{op3} {q3}")
        display_query = " ".join(parts)

        # Build filters dict understood by OERSearchEngine
        search_filters = {}

        # Resource type / language limits
        if adv_resource_type:
            search_filters.setdefault("resource_type", []).append(adv_resource_type)
        if adv_language:
            search_filters.setdefault("language", []).append(adv_language)

        # Identifier filters (exact/normalised)
        def _clean_identifier(value: str) -> str:
            # Strip spaces and common punctuation; keep digits/X
            import re
            return re.sub(r"[^0-9Xx]", "", value)

        identifier_filters = {}
        if q1 and f1 in ("isbn", "issn", "oclc"):
            identifier_filters[f1] = _clean_identifier(q1)
        if q2 and f2 in ("isbn", "issn", "oclc"):
            identifier_filters[f2] = _clean_identifier(q2)
        if q3 and f3 in ("isbn", "issn", "oclc"):
            identifier_filters[f3] = _clean_identifier(q3)

        if identifier_filters:
            # Merge into search_filters using your model field names
            # Adjust keys to match OERResource fields (e.g. isbn, issn, oclc_number)
            if "isbn" in identifier_filters:
                search_filters.setdefault("isbn", []).append(identifier_filters["isbn"])
            if "issn" in identifier_filters:
                search_filters.setdefault("issn", []).append(identifier_filters["issn"])
            if "oclc" in identifier_filters:
                search_filters.setdefault("oclc_number", []).append(identifier_filters["oclc"])

        # Build a free-text query string for hybrid_search from non-identifier fields
        free_text_clauses = []

        def _append_clause(term, field, op):
            if not term:
                return
            # For now, just append the term; you could add field hints later
            if not free_text_clauses:
                free_text_clauses.append(term)
            else:
                free_text_clauses.append(f"{op} {term}")

        if q1 and f1 not in ("isbn", "issn", "oclc"):
            _append_clause(q1, f1, "AND")
        if q2 and f2 not in ("isbn", "issn", "oclc"):
            _append_clause(q2, f2, op2)
        if q3 and f3 not in ("isbn", "issn", "oclc"):
            _append_clause(q3, f3, op3)

        query_string = " ".join(free_text_clauses).strip()

        detailed_results = []
        facets = {}
        sort_by = "relevance"

        if query_string or identifier_filters:
            engine = OERSearchEngine()

            results = engine.hybrid_search(
                query=query_string or "",  # empty ok if pure identifier search
                filters=search_filters if search_filters else None,
                limit=50,
            )

            results = engine.sort_results(results, sort_by=sort_by)

            facets = engine.get_facets(
                query=query_string or display_query or "",
                applied_filters=search_filters if search_filters else None,
            )

            detailed_results = results

            # Store for export as with ai_search
            request.session["last_search_results"] = [
                {
                    "id": getattr(r.resource, "id", None),
                    "title": getattr(r.resource, "title", ""),
                    "url": getattr(r.resource, "url", ""),
                    "score": float(r.final_score),
                    "source": getattr(r.resource.source, "name", ""),
                }
                for r in results
            ]

        # Reuse the ai_search template so UI is consistent
        context = {
            "query": display_query,
            "detailed_results": detailed_results,
            "facets": facets,
            "applied_filters": {
                "sources": request.GET.getlist("source"),
                "languages": request.GET.getlist("language"),
                "resource_types": request.GET.getlist("resource_type"),
                "subjects": request.GET.getlist("subject"),
            },
            "sort_by": sort_by,
            "ai_search": True,
            "advanced": True,
        }
        return render(request, TEMPLATE_ADVANCED_SEARCH, context)


    except Exception as e:
        messages.error(request, f"An error occurred during advanced search: {e}")
        return render(request, TEMPLATE_SEARCH, {
            "query": "",
            "detailed_results": [],
            "facets": {},
            "applied_filters": {
                "sources": [], "languages": [], "resource_types": [], "subjects": []
            },
            "sort_by": "relevance",
            "ai_search": True,
            "advanced": True,
        })


# Home View - Use the existing template
def home(request):
    """Home dashboard view"""
    try:
        context = {
            'total_resources': OERResource.objects.count(),
            'total_sources': OERSource.objects.count(),
            'recent_jobs': HarvestJob.objects.order_by('-started_at')[:5]
        }
        # Use the existing home template from templates/resources/
        return render(request, TEMPLATE_RESOURCES_HOME, context)
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}")
        # Fallback with empty context
        return render(request, TEMPLATE_RESOURCES_HOME, {
            'total_resources': 0,
            'total_sources': 0,
            'recent_jobs': []
        })

# CSV Operations
def csv_upload(request):
    """Handle CSV file uploads - Admin template"""
    try:
        if request.method == 'POST':
            form = CSVUploadForm(request.POST, request.FILES)
            
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                
                # Validate file type
                if not csv_file.name.lower().endswith(('.csv', '.tsv')):
                    messages.error(request, "Please upload a CSV or TSV file.")
                    return redirect('resources:csv_upload')
                
                delimiter = ',' if csv_file.name.lower().endswith('.csv') else '\t'
                reader = csv.DictReader(
                    io.TextIOWrapper(csv_file.file, encoding='utf-8'),
                    delimiter=delimiter
                )
                
                # Process CSV data here
                processed_count = 0
                for row in reader:
                    # Add your CSV processing logic here
                    processed_count += 1
                
                messages.success(request, f"Successfully processed {processed_count} records from '{csv_file.name}'.")
                return redirect('resources:csv_upload')
            else:
                logger.error(f"Invalid form submission in csv_upload: {form.errors}")
                messages.error(request, "Error validating the form.")
                return redirect('resources:csv_upload')
        else:
            form = CSVUploadForm()
            
        return render(request, TEMPLATE_CSV_UPLOAD, {'form': form})
    except Exception as e:
        logger.error(f"Error in csv_upload: {str(e)}")
        messages.error(request, "An error occurred during file upload.")
        return redirect('resources:csv_upload')

@staff_required
def add_oer_source(request):
    """
    Staff-only view for adding an OERSource using supplier-first presets.
    """
    if request.method == "POST":
        form = OERSourceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "OER source created.")
            return redirect("admin:resources_oersource_changelist")
    else:
        form = OERSourceForm()

    presets_for_ui = []
    for preset_id, entry in SUPPLIER_PRESETS.items():
        proto = entry["protocol"]
        preset_key = entry["preset_key"]

        config = {}
        if preset_key and proto in PRESET_CONFIGS:
            config = PRESET_CONFIGS[proto].get(preset_key, {}) or {}

        presets_for_ui.append(
            {
                "id": preset_id,
                "label": entry["label"],
                "protocol": proto,
                "preset_key": preset_key,
                "supplier": entry["supplier"],
                "content_scope": entry["content_scope"],
                "api_endpoint": config.get("api_endpoint", ""),
                "oaipmh_url": config.get("oaipmh_url", ""),
                "csv_url": config.get("csv_url", ""),
                "marcxml_url": config.get("marcxml_url", ""),
                "request_params": config.get("request_params", {}),
                "request_headers": config.get("request_headers", {}),
            }
        )

    presets_for_ui.sort(key=lambda p: p["label"].lower())

    context = {
        "form": form,
        "oer_presets_json": json.dumps(presets_for_ui),
    }
    return render(request, "admin/resources/add_oer_source.html", context)



@staff_required
def kbart_upload(request):
    """Upload or provide a URL for a KBART (TSV) file and import as OERResources."""
    try:
        # Preselect source if provided in querystring
        preselected_source_id = request.GET.get('source_id') or request.POST.get('source_id')

        if request.method == 'POST':
            form = KBARTUploadForm(request.POST, request.FILES)
            if form.is_valid():
                kbart_file = form.cleaned_data.get('kbart_file')
                kbart_url = form.cleaned_data.get('kbart_url')
                source = form.cleaned_data.get('source')
                create_name = form.cleaned_data.get('create_source_name')

                # Resolve or create source
                if not source and create_name:
                    source = OERSource.objects.create(name=create_name, display_name=create_name, source_type='CSV')

                if not source:
                    messages.error(request, "Please select a source or provide a name to create one.")
                    return redirect('resources:kbart_upload')

                harvester = None
                from .harvesters.kbart_harvester import KBARTHarvester
                harvester = KBARTHarvester()

                if kbart_file:
                    # process uploaded file directly
                    job = harvester.harvest_from_fileobj(source, kbart_file)
                else:
                    # path is URL
                    job = harvester.harvest_from_path(source, kbart_url)

                messages.success(request, f"KBART harvest completed: created={job.resources_created} updated={job.resources_updated} failed={job.resources_failed}")
                return redirect('resources:kbart_upload')
            else:
                messages.error(request, "Invalid form submission.")
                return redirect('resources:kbart_upload')
        else:
            initial = {}
            if preselected_source_id:
                initial['source'] = preselected_source_id
            form = KBARTUploadForm(initial=initial)

        return render(request, 'admin/resources/kbart_upload.html', {'form': form})
    except Exception as e:
        logger.exception('Error in kbart_upload: %s', e)
        messages.error(request, f"Error importing KBART: {e}")
        return redirect('resources:kbart_upload')


# =====================================================================
# Resource Detail Pages (NEW)
# =====================================================================

def resource_shortlink(request, pk):
    """Short URL redirect to full detail page (e.g., /r/123/ → /resource/123/)"""
    return redirect("resources:resource_detail", pk=pk, permanent=True)


def resource_detail(request, pk):
    """
    Per-resource detail page with:
    - Rich metadata + external links
    - Optional AI summary (precomputed, no live LLM)
    - Related resources via vector similarity
    
    Performance: 1 DB fetch + 1 vector search, no LLM calls at request time.
    """
    try:
        resource = (
            OERResource.objects
            .select_related("source")
            .get(pk=pk)
        )
    except OERResource.DoesNotExist:
        messages.error(request, "Resource not found.")
        return redirect("resources:ai_search")

    # Build related items using semantic search on the resource's own content
    related_results = []
    try:
        # Use extracted_text if available, else description, else title
        base_text = (
            (resource.extracted_text or "")[:2000]
            or (resource.description or "")
            or resource.title
        )

        if base_text:
            engine = OERSearchEngine()
            related_results = engine.semantic_search(
                query=base_text,
                limit=6,
            )
            # Drop self if present
            related_results = [
                r for r in related_results
                if r.resource.id != resource.id
            ][:5]  # Keep top 5 related items
    except Exception as e:
        logger.warning(f"Error fetching related resources for {pk}: {e}")
        related_results = []

    # Read precomputed AI summary if it exists (no live LLM call)
    ai_summary = getattr(resource, "ai_summary", None)

    context = {
        "resource": resource,
        "related_results": related_results,
        "ai_summary": ai_summary,
    }
    return render(request, "resources/resource_detail.html", context)


def csv_download(request):
    """Download resources as CSV"""
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="oer_resources.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Title', 'Description', 'URL', 'License', 'Source'])
        
        for resource in OERResource.objects.all():
            writer.writerow([
                resource.title,
                resource.description,
                resource.url,
                resource.license,
                resource.source.name if resource.source else ''
            ])
        
        return response
    except Exception as e:
        logger.error(f"Error in csv_download: {str(e)}")
        messages.error(request, "An error occurred while generating the CSV file.")
        return redirect('resources:home')

# Export Views
def export_to_talis(request):
    try:
        # NEW: handle POST from Talis AI report (checkboxes + action)
        if request.method == "POST" and request.POST.getlist("selected_resources"):
            from django.http import HttpResponse  # ensure this import exists at top of file
            from .models import TalisPushJob     # these are already imported in this file
            from .tasks import talis_push_report

            selected_ids = request.POST.getlist("selected_resources")
            action = request.POST.get("action")
            talis_title = (request.POST.get("talis_title") or "").strip()
            talis_description = (request.POST.get("talis_description") or "").strip()

            resources = OERResource.objects.filter(id__in=selected_ids)

            if not resources.exists():
                messages.error(request, "No resources were selected for export.")
                return redirect("resources:talis_report_dashboard")

            if action == "download_csv":
                import csv

                filename = (talis_title or "oer_phoenix_talis_list").replace(" ", "_")
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = f'attachment; filename=\"{filename}.csv\"'

                writer = csv.writer(response)
                # Adjust headers to match your Talis CSV template as needed
                writer.writerow(["Title", "Author", "Web address", "Notes"])

                for r in resources:
                    writer.writerow([
                        r.title,
                        getattr(r, "authors", "") or "",
                        r.url or "",
                        talis_description,
                    ])

                return response

            elif action == "push_talis":
                job = TalisPushJob.objects.create(
                    title=talis_title or "OER_Phoenix export",
                    description=talis_description,
                    report_snapshot=[{
                        "id": int(r.pk),
                        "title": r.title,
                        "url": r.url,
                    } for r in resources],
                )
                talis_push_report.delay(job.id)

                messages.success(
                    request,
                    "Talis export job started. You can monitor progress on the Talis jobs page."
                )
                return redirect("resources:export_success")

            else:
                messages.error(request, "No export action was selected.")
                return redirect("resources:talis_report_dashboard")

        # FALLBACK: existing export form at /export/talis/
        if request.method == 'POST':
            form = TalisExportForm(request.POST)
            if form.is_valid():
                selected_resources = form.cleaned_data['resource_ids']
                if not selected_resources.exists():
                    messages.error(request, "No resources were selected for export.")
                    return redirect('resources:export_to_talis')

                request.session['export_resources'] = list(
                    selected_resources.values_list('id', flat=True)
                )
                request.session['talis_title'] = form.cleaned_data['title']
                request.session['talis_description'] = form.cleaned_data.get('description', '')
                return redirect('resources:talis_preview')
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = TalisExportForm()

        return render(request, 'resources/export.html', {'form': form})

    except Exception as e:
        logger.error(f"Error in export_to_talis: {str(e)}")
        messages.error(request, "An error occurred during the export process.")
        return redirect('resources:home')


def talis_preview(request):
    try:
        resource_ids = request.session.get('export_resources', [])
        resources = OERResource.objects.filter(id__in=resource_ids) if resource_ids else []
        return render(request, TEMPLATE_TALIS_PREVIEW, {
            'resources': resources,
            'talis_title': request.session.get('talis_title', ''),
            'talis_description': request.session.get('talis_description', '')
        })
    except Exception as e:
        logger.error(f"Error in talis_preview: {str(e)}")
        messages.error(request, "An error occurred while loading the preview.")
        return redirect('resources:home')

# Harvesting Views
@staff_required
def harvest_view(request, source_id):
    try:
        source = get_object_or_404(OERSource, pk=source_id)

        if request.method == 'POST':
            # Determine the harvester class based on source configuration
            if source.source_type == 'API':
                harvester = APIHarvester(source)
            elif source.source_type == 'OAIPMH':
                harvester = OAIPMHHarvester(source)
            elif source.source_type == 'CSV':
                harvester = CSVHarvester(source)
            elif source.source_type == "MARCXML":
                harvester = MARCXMLHarvester(source)
            else:
                messages.error(request, f"Unsupported harvester type: {source.source_type}")
                return redirect('admin:resources_oersource_changelist')

            # Start harvest job
            job = harvester.harvest()
            source.status = 'active'
            source.save(update_fields=['status'])
            messages.success(request, f"Started harvesting from {source.name} (Job: {getattr(job, 'id', None)})")
            return redirect('admin:resources_harvestjob_changelist')

        return render(request, TEMPLATE_OERSOURCE_HARVEST, {'source': source})
    except Exception as e:
        logger.error(f"Error in harvest_view: {str(e)}")
        messages.error(request, f"Error starting harvest: {str(e)}")
        return redirect('admin:resources_oersource_changelist')

@staff_required
def test_connection_view(request, source_id):
    """Handle test connection request for an OER source"""
    try:
        source = get_object_or_404(OERSource, pk=source_id)
        
        # Determine the harvester class based on source configuration
        if source.source_type == 'API':
            harvester = APIHarvester(source)
        elif source.source_type == 'OAIPMH':
            harvester = OAIPMHHarvester(source)
        elif source.source_type == 'CSV':
            harvester = CSVHarvester(source)
        elif source.source_type == "MARCXML":
            harvester = MARCXMLHarvester(source)
        else:
            messages.error(request, f"Unsupported harvester type: {source.source_type}")
            return redirect('admin:resources_oersource_changelist')

        success = harvester.test_connection()

        if success:
            source.status = 'active'
            source.save(update_fields=['status'])
            messages.success(request, f"Successfully connected to {source.name}")
        else:
            source.status = 'error'
            source.save(update_fields=['status'])
            messages.warning(request, f"Could not connect to {source.name}")
            
    except Exception as e:
        logger.error(f"Error in test_connection_view: {str(e)}")
        messages.error(request, f"Connection error: {str(e)}")
    
    return redirect('admin:resources_oersource_changelist')

# Source Management Views
@staff_required
@require_http_methods(['GET', 'POST'])
def create_source(request):
    """Create a new OER source - Admin template"""
    try:
        if request.method == 'POST':
            source_type = request.POST.get('source_type')
            form_class = get_form_class(source_type)
            
            if not form_class:
                messages.error(request, "Invalid source type.")
                return redirect('admin:resources_oersource_changelist')
                
            form = form_class(request.POST)
            if form.is_valid():
                source = form.save()
                messages.success(request, f"Successfully created {source_type} source: {source.name}")
                return redirect('admin:resources_oersource_changelist')
            else:
                logger.error(f"Invalid form submission in create_source: {form.errors}")
                messages.error(request, "Error validating the form.")
        else:
            # GET request - show source type selection
            return render(request, 'admin/resources/create_source.html')
        
        # If form is invalid, re-render with errors
        context = {
            'form': form,
            'source_type': source_type
        }
        return render(request, TEMPLATE_CREATE_SOURCE, context)
    except Exception as e:
        logger.error(f"Error in create_source: {str(e)}")
        messages.error(request, "An error occurred while creating the source.")
        return redirect('admin:resources_oersource_changelist')

def get_form_class(source_type):
    """Helper function to determine form class based on source type"""
    form_classes = {
        'API': APIHarvesterForm,
        'OAIPMH': OAIPMHHarvesterForm,
        'CSV': CSVHarvesterForm
    }
    return form_classes.get(source_type)

@staff_required
def generate_missing_embeddings(request):
    """
    Staff-only view to trigger embedding generation for all resources missing embeddings.
    """
    try:
        from resources.services import ai_utils
        
        # Count resources needing embeddings
        resources_needing = OERResource.objects.filter(content_embedding__isnull=True).count()
        
        if resources_needing == 0:
            messages.info(request, "All resources already have embeddings.")
            return redirect('resources:dashboard')
        
        # Trigger generation
        ai_utils.generate_embeddings()
        
        messages.success(
            request,
            f"Embedding generation triggered for {resources_needing} resources. This may take several minutes."
        )
    except Exception as e:
        logger.error(f"Error triggering embedding generation: {str(e)}")
        messages.error(request, f"Failed to trigger embedding generation: {str(e)}")
    
    return redirect('resources:dashboard')


@staff_required
@require_http_methods(['GET'])
def load_configuration_form(request):
    """Load configuration form based on source type"""
    try:
        source_type = request.GET.get('source_type')
        form_class = get_form_class(source_type)
        
        if not form_class:
            return JsonResponse({'error': 'Invalid source type'}, status=400)
            
        form = form_class()
        
        # Render form to HTML string
        form_html = render(request, 'admin/resources/partials/source_config_form.html', {'form': form}).content.decode()
        
        return JsonResponse({'form_html': form_html})
    except Exception as e:
        logger.error(f"Error in load_configuration_form: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_required
def add_preset_view(request):
    """
    Add preset harvester view - Admin template.

    Shows the appropriate preset list for the chosen harvester type
    (API, OAIPMH, CSV, or MARCXML).
    """
    harvester_type = request.GET.get("type", "API")

    # Basic guard: only allow known types
    if harvester_type not in PRESET_CONFIGS:
        messages.error(request, "Invalid harvester type.")
        return redirect("admin:resources_oersource_changelist")

    presets = PRESET_CONFIGS.get(harvester_type, {})

    context = {
        "harvester_type": harvester_type,
        "presets": presets,
    }
    return render(request, TEMPLATE_ADD_HARVESTER, context)


@staff_required
def apply_preset_view(request):
    """Apply a preset configuration to create a new source"""
    if request.method == 'POST':
        try:
            source_type = request.POST.get('source_type')
            preset_key = request.POST.get('preset_key')
            
            if not source_type or not preset_key:
                messages.error(request, "Missing source type or preset key.")
                return redirect('admin:resources_oersource_add')
            
            # Get the preset configuration
            preset = PRESET_CONFIGS.get(source_type, {}).get(preset_key)
            
            if not preset:
                messages.error(request, f"Preset not found: {preset_key}")
                return redirect('admin:resources_oersource_add')
            
            # Use dicts directly for JSONFields
            request_params = preset.get('request_params', {})
            request_headers = preset.get('request_headers', {})

            # Create the source with preset values (JSONFields accept dicts)
            source = OERSource.objects.create(
                name=preset['name'],
                description=preset['description'],
                source_type=source_type,
                api_endpoint=preset.get('api_endpoint', ''),
                oaipmh_url=preset.get('oaipmh_url', ''),
                csv_url=preset.get('csv_url', ''),
                request_params=request_params,
                request_headers=request_headers,
                oaipmh_set_spec=preset.get('oaipmh_set_spec', ''),
                harvest_schedule=preset.get('harvest_schedule', 'manual'),
                max_resources_per_harvest=preset.get('max_resources_per_harvest', 1000),
                is_active=True
            )
            
            messages.success(request, f"Successfully created {getattr(source, 'name', '(no name)')} from preset.")
            return redirect('admin:resources_oersource_change', object_id=getattr(source, 'id', None))

            
        except Exception as e:
            logger.error(f"Error applying preset: {str(e)}")
            messages.error(request, f"Error applying preset: {str(e)}")
            return redirect('admin:resources_oersource_add')
    
    return redirect('admin:resources_oersource_add')

# Export Functions
def export_resources(request):
    """Export resources view for regular users (non-admin)"""
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            export_type = form.cleaned_data['export_type']
            
            if export_type == 'CSV':
                return export_csv(request)
            elif export_type == 'JSON':
                return export_json(request)
    else:
        form = ExportForm()
    
    # Add statistics to context
    total_resources = OERResource.objects.count()
    active_resources = OERResource.objects.filter(is_active=True).count()
    
    return render(request, TEMPLATE_EXPORT, {
        'form': form,
        'total_resources': total_resources,
        'active_resources': active_resources,
    })

def export_csv(request):
    """Export resources as CSV for regular users"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="oer_resources.csv"'
    
    writer = csv.writer(response)
    # Write CSV header
    writer.writerow([
        'Title', 'Description', 'URL', 'License', 'Subject', 
        'Level', 'Publisher', 'Author', 'Language', 'Resource Type',
        'Source', 'Created Date'
    ])
    
    # Write data rows
    for resource in OERResource.objects.all():
        writer.writerow([
            resource.title,
            resource.description,
            resource.url,
            resource.license,
            resource.subject,
            resource.level,
            resource.publisher,
            resource.author,
            resource.language,
            resource.resource_type,
            resource.source.name if resource.source else '',
            resource.created_at.strftime('%Y-%m-%d') if resource.created_at else ''
        ])
    
    return response

def export_json(request):
    """Export resources as JSON for regular users"""
    resources = OERResource.objects.all()
    data = serializers.serialize('json', resources)
    
    response = JsonResponse({'resources': data}, safe=False)
    response['Content-Disposition'] = 'attachment; filename="oer_resources.json"'
    return response

# Bulk Operations
@staff_required
def bulk_csv_upload(request):
    """Handle bulk CSV file uploads - Admin template"""
    try:
        if request.method == 'POST':
            form = CSVUploadForm(request.POST, request.FILES)
            
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                
                # Validate file type
                if not csv_file.name.lower().endswith(('.csv', '.tsv')):
                    messages.error(request, "Please upload a CSV or TSV file.")
                    return redirect('resources:bulk_csv_upload')
                
                delimiter = ',' if csv_file.name.lower().endswith('.csv') else '\t'
                reader = csv.DictReader(
                    io.TextIOWrapper(csv_file.file, encoding='utf-8'),
                    delimiter=delimiter
                )
                
                # Process the file
                processed_count = 0
                for row in reader:
                    # Add bulk processing logic here
                    processed_count += 1
                
                messages.success(request, f"Bulk upload completed. Processed {processed_count} records.")
                return redirect('resources:bulk_csv_upload')
            else:
                logger.error(f"Invalid form submission in bulk_csv_upload: {form.errors}")
                messages.error(request, "Error validating the form.")
                return redirect('resources:bulk_csv_upload')
        else:
            form = CSVUploadForm()
            
        return render(request, TEMPLATE_BULK_CSV_UPLOAD, {'form': form})
    except Exception as e:
        logger.error(f"Error in bulk_csv_upload: {str(e)}")
        messages.error(request, "An error occurred during bulk file upload.")
        return redirect('resources:home')


def process_talis_csv(request):
    """Process an uploaded Talis CSV: run AI search per line and render a report."""
    from .forms import CSVUploadForm
    from .services.search_engine import OERSearchEngine
    import csv
    import io

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Please upload a valid CSV file.")
            return redirect('resources:talis_csv_upload')

        csv_file = request.FILES['csv_file']
        # Use DictReader to be tolerant of columns
        text = io.TextIOWrapper(csv_file.file, encoding='utf-8')
        reader = csv.DictReader(text)

        engine = OERSearchEngine()
        report = []
        for row in reader:
            title = row.get('Title') or row.get('title') or row.get('Item Title') or ''
            author = row.get('Author') or row.get('author') or ''
            note = row.get('Note for Student') or row.get('Note') or ''
            query = ' '.join([title, author, note]).strip()
            if not query:
                query = title or author or ''

            matches = []
            if query:
                results = engine.hybrid_search(query, limit=5)
                for r in results:
                    matches.append({
                        'id': getattr(r.resource, 'id', None),
                        'title': getattr(r.resource, 'title', ''),
                        'url': getattr(r.resource, 'url', ''),
                        'final_score': float(r.final_score),
                        'match_reason': r.match_reason,
                        'source': getattr(r.resource.source, 'name', '')
                    })

            report.append({
                'original': {'title': title, 'author': author, 'note': note},
                'matches': matches
            })

        # Store report in session for download
        request.session['talis_report'] = report
        return render(request, 'resources/talis_report.html', {'report': report})

    return redirect('resources:talis_csv_upload')


def talis_report_download(request):
    """Download the last Talis report stored in session as CSV."""
    import csv
    from django.http import HttpResponse

    report = request.session.get('talis_report')
    if not report:
        messages.error(request, "No report available to download.")
        return redirect('resources:talis_csv_upload')

    # Build CSV in memory
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="talis_ai_report.csv"'
    writer = csv.writer(response)
    # Header
    writer.writerow(['Original Title', 'Original Author', 'Matched Resource ID', 'Matched Title', 'Matched URL', 'Score', 'Source'])

    for item in report:
        orig = item.get('original', {})
        matches = item.get('matches', [])
        if not matches:
            writer.writerow([orig.get('title', ''), orig.get('author', ''), '', '', '', '', ''])
        else:
            for m in matches:
                writer.writerow([orig.get('title', ''), orig.get('author', ''), m.get('id'), m.get('title'), m.get('url'), m.get('final_score'), m.get('source')])

    return response


def talis_push(request):
    """Push the last Talis report to a configured TALIS API endpoint."""
    from django.conf import settings
    import requests

    report = request.session.get('talis_report')
    if not report:
        messages.error(request, "No report available to push to Talis.")
        return redirect('resources:talis_csv_upload')

    talis_url = getattr(settings, 'TALIS_API_URL', None)
    if not talis_url:
        messages.error(request, "Talis API URL not configured. Set TALIS_API_URL in settings.")
        return redirect('resources:talis_csv_upload')

    # Create a TalisPushJob and enqueue async task
    try:
        job = TalisPushJob.objects.create(
            target_url=talis_url,
            report_snapshot=report,
            status='pending'
        )
        from .tasks import talis_push_report  # Ensure this is a Celery task, not a list
        job_id = getattr(job, 'id', None)
        messages.success(request, f'Report queued for push (Job {job_id}).')
    except Exception as e:
        messages.error(request, f'Failed to queue push job: {str(e)}')

    return redirect('resources:talis_csv_upload')


def search_export_talis(request):
    """Export the last AI search results stored in session as a CSV compatible with Talis."""
    import csv
    from django.http import HttpResponse

    report = request.session.get('last_search_results')
    if not report:
        messages.error(request, "No recent search results available to export.")
        return redirect('resources:ai_search')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="search_talis_export.csv"'
    writer = csv.writer(response)
    # Header - keep Talis-friendly columns
    writer.writerow(['Original Query', 'Matched Resource ID', 'Matched Title', 'Matched URL', 'Score', 'Source'])

    # No original query stored per-item; write blank for now
    for item in report:
        writer.writerow(['', item.get('id', ''), item.get('title', ''), item.get('url', ''), item.get('final_score', ''), item.get('source', '')])

    return response


@staff_required
def talis_jobs(request):
    """Simple staff-only view listing TalisPushJob records for demo/admin."""
    try:
        jobs = TalisPushJob.objects.order_by('-created_at')[:100]
        return render(request, 'resources/talis_jobs.html', {'jobs': jobs})
    except Exception as e:
        logger.error(f"Error in talis_jobs view: {str(e)}")
        messages.error(request, "Unable to load Talis push jobs.")
        return redirect('resources:home')
    

@staff_required
def export_data(request):
    """General data export view admin"""
    try:
        if request.method == 'POST':
            form = ExportForm(request.POST)
            
            if form.is_valid():
                export_type = form.cleaned_data['export_type']
                
                if export_type == 'CSV':
                    return export_csv(request)
                elif export_type == 'JSON':
                    return export_json(request)
            else:
                logger.error(f"Invalid form submission in export_data: {form.errors}")
                messages.error(request, "Error validating the form.")
        else:
            form = ExportForm()
        
        return render(request, TEMPLATE_EXPORT_DATA, {'form': form})
    except Exception as e:
        logger.error(f"Error in export_data: {str(e)}")
        messages.error(request, "An error occurred during data export.")
        return redirect('admin:index')

# Success Views
def export_success(request):
    """Show export success page"""
    try:
        return render(request, TEMPLATE_EXPORT_SUCCESS)
    except Exception as e:
        logger.error(f"Error in export_success: {str(e)}")
        messages.error(request, "An error occurred while displaying the success page.")
        return redirect('resources:home')


def search_consumer(request):
    """Render a simple frontend that consumes the DRF search API."""
    return render(request, 'resources/search_api_consumer.html')


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def rag_test_view(request):
    """
    Internal test interface for the RAG (Retrieval-Augmented Generation) endpoint.
    
    Restricted to staff/superusers to prevent abuse during testing phase.
    Renders a form that POSTs to /api/rag-answer/ and displays the LLM-generated answer.
    """
    return render(request, 'rag_test.html')
