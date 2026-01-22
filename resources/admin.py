# admin.py
"""
Enhanced Django Admin for OER Source Management
Uses unified form with JavaScript for dynamic behavior
"""

import json
import requests
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect, JsonResponse
from django import forms
from django.db.models import Count, Q, F

from resources.models import OERSource, HarvestJob, OERSourceFieldMapping, OERResource
from resources.models import TalisPushJob
from resources.harvesters.api_harvester import APIHarvester
from resources.harvesters.oaipmh_harvester import OAIPMHHarvester
from resources.harvesters.csv_harvester import CSVHarvester
from resources.harvesters.marcxml_harvester import MARCXMLHarvester
from resources.forms import OERSourceForm  # Import the unified form
from resources.harvesters.kbart_harvester import KBARTHarvester
from resources.services import ai_utils  # NEW: for embedding generation
from resources.services import metadata_enricher

# ---------------------------------------------------------------------------- #
#                               Admin Actions                                   #
# ---------------------------------------------------------------------------- #

@admin.action(description="Generate embeddings for selected resources")
def generate_embeddings_action(modeladmin, request, queryset):
    """
    Admin action to generate embeddings for selected OERResource instances.
    """
    updated = 0
    failed = 0
    
    for resource in queryset:
        success = ai_utils.compute_and_store_embedding_for_resource(resource.id)
        if success:
            updated += 1
        else:
            failed += 1
    
    if failed > 0:
        modeladmin.message_user(
            request,
            f"Generated embeddings for {updated} resources. {failed} failed.",
            level=messages.WARNING
        )
    else:
        modeladmin.message_user(
            request,
            f"Successfully generated embeddings for {updated} resources.",
            level=messages.SUCCESS
        )

@admin.action(description="Run quality assessment for selected resources")
def run_quality_assessment_action(modeladmin, request, queryset):
    """
    Admin action to run quality assessment for selected OERResource instances.
    """
    from resources.services.quality_assessment import QualityAssessmentService
    
    qa_service = QualityAssessmentService()
    updated = 0
    failed = 0
    
    for resource in queryset:
        try:
            result = qa_service.assess_resource(resource)
            resource.overall_quality_score = result['overall_score']
            resource.save(update_fields=['overall_quality_score'])
            updated += 1
        except Exception as e:
            failed += 1
            modeladmin.message_user(
                request,
                f"Failed to assess {resource.title}: {str(e)}",
                level=messages.ERROR
            )
    
    if failed > 0:
        modeladmin.message_user(
            request,
            f"Assessed {updated} resources. {failed} failed.",
            level=messages.WARNING
        )
    else:
        modeladmin.message_user(
            request,
            f"Successfully assessed {updated} resources.",
            level=messages.SUCCESS
        )

@admin.action(description="Run quality assessment for ALL resources (batch)")
def run_quality_assessment_all_action(modeladmin, request, queryset):
    """
    Admin action to run quality assessment for ALL resources in the database.
    This ignores the selection and processes everything.
    """
    from resources.services.quality_assessment import QualityAssessmentService
    
    qa_service = QualityAssessmentService()
    
    # Get all resources that need assessment (either no score or outdated)
    all_resources = OERResource.objects.filter(overall_quality_score__isnull=True) | \
                    OERResource.objects.filter(overall_quality_score__lt=0)
    
    total = all_resources.count()
    
    if total == 0:
        modeladmin.message_user(
            request,
            "All resources already have quality scores.",
            level=messages.INFO
        )
        return
    
    updated = 0
    failed = 0
    
    for resource in all_resources:
        try:
            result = qa_service.assess_resource(resource)
            resource.overall_quality_score = result['overall_score']
            resource.save(update_fields=['overall_quality_score'])
            updated += 1
        except Exception as e:
            failed += 1
    
    if failed > 0:
        modeladmin.message_user(
            request,
            f"Batch assessment complete: {updated}/{total} successful, {failed} failed.",
            level=messages.WARNING
        )
    else:
        modeladmin.message_user(
            request,
            f"Batch assessment complete: All {updated} resources assessed successfully.",
            level=messages.SUCCESS
        )

# ---------------------------------------------------------------------------- #
#                               Custom Filters                                  #
# ---------------------------------------------------------------------------- #

class HasEmbeddingsFilter(admin.SimpleListFilter):
    """Filter OERSources by embedding completeness"""
    title = "resource embeddings"
    parameter_name = "has_embeddings"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Resources with embeddings"),
            ("no", "Resources without embeddings"),
        ]


    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        qs = queryset.annotate(
            total_resources=Count("resources"),
            with_embeddings=Count("resources", filter=Q(resources__content_embedding__isnull=False)),
        ).filter(total_resources__gt=0)


        if self.value() == "yes":
            return qs.filter(total_resources=F("with_embeddings"))
        if self.value() == "no":
            return qs.exclude(total_resources=F("with_embeddings"))
        return qs

# ---------------------------------------------------------------------------- #
#                               Inline Admin                                    #
# ---------------------------------------------------------------------------- #

class OERSourceFieldMappingInline(admin.TabularInline):
    model = OERSourceFieldMapping
    extra = 1

# ---------------------------------------------------------------------------- #
#                               OER Source Admin                               #
# ---------------------------------------------------------------------------- #

@admin.register(OERSource)
class OERSourceAdmin(admin.ModelAdmin):
    form = OERSourceForm  # Use the unified form
    list_display = ['name', 'source_type', 'status_badge', 'last_harvest_display', 'resource_count', 'embedded_count', 'harvest_action_buttons']
    list_filter = ['source_type', 'status', 'is_active', HasEmbeddingsFilter]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_harvested', 'last_harvest_at']
    
    # Add JavaScript for dynamic form behavior
    class Media:
        js = ('admin/js/oer_source_dynamic.js',)
    
    def get_fieldsets(self, request, obj=None):
        """Single fieldset structure that works for all source types"""
        fieldsets = [
            ('Basic Information', {
                'fields': ('name', 'description', 'source_type', 'is_active')
            }),
            ('Harvest Configuration', {
                'fields': ('harvest_schedule', 'max_resources_per_harvest')
            }),
            ('API Configuration', {
                'fields': ('api_endpoint', 'api_key', 'request_headers', 'request_params'),
                'classes': ('api-config',)
            }),
            ('OAI-PMH Configuration', {
                'fields': ('oaipmh_url', 'oaipmh_set_spec'),
                'classes': ('oaipmh-config',)
            }),
            ('CSV Configuration', {
                'fields': ('csv_url',),
                'classes': ('csv-config',)
            }),
            ('MARCXML Configuration', {
                'fields': ('marcxml_url',),
                'classes': ('marcxml-config',)
            }),
            ('Status & Metadata', {
                'fields': ('status', 'total_harvested', 'last_harvest_at', 'created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        ]
        return fieldsets

    def save_model(self, request, obj, form, change):
        """Handle saving with proper status setting"""
        if not change:  # New object
            # Set default status based on source_type
            if obj.source_type == 'API':
                obj.status = 'testing'
            elif obj.source_type == 'OAIPMH':
                obj.status = 'active'
            elif obj.source_type == 'CSV':
                obj.status = 'active'
            elif obj.source_type == 'MARCXML':
                obj.status = 'active'
        
        super().save_model(request, obj, form, change)

        # If a KBART file was uploaded in the admin form, process it immediately
        try:
            kbart_file = None
            if hasattr(form, 'cleaned_data'):
                kbart_file = form.cleaned_data.get('kbart_file')

            if kbart_file:
                harvester = KBARTHarvester()
                job = harvester.harvest_from_fileobj(obj, kbart_file)
                self.message_user(request, f"KBART import complete: created={job.resources_created} updated={job.resources_updated} failed={job.resources_failed}")
        except Exception as e:
            self.message_user(request, f"KBART import failed: {e}", level=messages.ERROR)

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'gray', 
            'testing': 'orange',
            'error': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def last_harvest_display(self, obj):
        if obj.last_harvest_at:
            return obj.last_harvest_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em>Never</em>')
    last_harvest_display.short_description = 'Last Harvest'

    def resource_count(self, obj):
        """Display total resource count for this source"""
        return obj.resources.count()
    resource_count.short_description = 'Resources'

    def embedded_count(self, obj):
        """Display count of resources with embeddings"""
        return obj.resources.filter(content_embedding__isnull=False).count()
    embedded_count.short_description = 'With Embedding'

    def harvest_action_buttons(self, obj):
        if not obj.is_active:
            return format_html('<em>Inactive</em>')
        
        harvest_url = reverse('admin:resources_oersource_harvest', args=[obj.pk])
        test_url = reverse('admin:resources_oersource_test', args=[obj.pk])
        
        return format_html(
            '''
            <a class="button" href="{}" style="background-color: #417690; color: white; 
            padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;">🌾 Harvest</a>
            <br>
            <a class="button" href="{}" style="background-color: #28a745; color: white; 
            padding: 5px 10px; text-decoration: none; border-radius: 3px;">🧪 Test</a>
            ''',
            harvest_url, test_url
        )
    harvest_action_buttons.short_description = 'Actions'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('harvest/<int:source_id>/', self.admin_site.admin_view(self.harvest_view), name='resources_oersource_harvest'),
            path('test/<int:source_id>/', self.admin_site.admin_view(self.test_connection_view), name='resources_oersource_test'),
        ]
        return custom_urls + urls

    def harvest_view(self, request, source_id):
        """Handle harvesting for a specific source"""
        source = OERSource.objects.get(id=source_id)
        try:
            # Determine the harvester class based on source configuration
            if source.source_type == 'API':
                harvester = APIHarvester(source)
            elif source.source_type == 'OAIPMH':
                harvester = OAIPMHHarvester(source)
            elif source.source_type == 'CSV':
                harvester = CSVHarvester(source)
            elif source.source_type == 'MARCXML':
                harvester = MARCXMLHarvester(source)
            else:
                messages.error(request, f"Unsupported harvester type: {source.source_type}")
                return HttpResponseRedirect(reverse('admin:resources_oersource_changelist'))

            # Start harvest job - all BaseHarvester subclasses use harvest()
            job = harvester.harvest()
            
            source.status = 'active'
            source.save(update_fields=['status'])
            messages.success(request, f"Started harvesting from {source.name} (Job: {job.id})")
        except Exception as e:
            messages.error(request, f"Harvesting failed: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:resources_oersource_changelist'))

    def test_connection_view(self, request, source_id):
        """Test connection to the source endpoint based on source type."""
        source = self.get_object(request, source_id)
        
        if source is None:
            messages.error(request, "Source not found.")
            return HttpResponseRedirect(reverse('admin:resources_oersource_changelist'))
        
        success = False
        error_message = None
        test_url = None
        
        try:
            # Route based on source type and available endpoint
            if source.source_type == 'OAIPMH' and source.oaipmh_url:
                # Test OAI-PMH with Identify verb
                test_url = source.oaipmh_url.rstrip('?') + "?verb=Identify"
                response = requests.get(test_url, timeout=30)
                
                if response.status_code == 200:
                    # Check if response contains valid OAI-PMH XML
                    if 'OAI-PMH' in response.text and 'Identify' in response.text:
                        success = True
                    else:
                        error_message = "URL returned 200 but does not appear to be valid OAI-PMH"
                else:
                    error_message = f"HTTP {response.status_code}: {response.reason}"
            
            elif source.source_type == 'CSV' and source.csv_url:
                # Test CSV/KBART URL - check if file is accessible
                test_url = source.csv_url
                try:
                    response = requests.head(test_url, timeout=30, allow_redirects=True)
                    # If HEAD not supported, try GET with stream
                    if response.status_code == 405:
                        response = requests.get(test_url, timeout=30, stream=True)
                        response.close()
                except requests.exceptions.Timeout:
                    error_message = "Connection timed out after 30 seconds"
                    raise
                
                if response.status_code == 200:
                    success = True
                    # Optional: check Content-Type header
                    content_type = response.headers.get('Content-Type', '')
                    if content_type and 'text' not in content_type and 'csv' not in content_type and 'tsv' not in content_type:
                        messages.warning(request, f"Warning: Content-Type is '{content_type}' (expected text/csv or text/tab-separated-values)")
                else:
                    error_message = f"HTTP {response.status_code}: {response.reason}"
            
            elif source.source_type == 'MARCXML' and source.marcxml_url:
                # Test MARCXML URL - check if XML file is accessible
                test_url = source.marcxml_url
                try:
                    response = requests.head(test_url, timeout=30, allow_redirects=True)
                    # If HEAD not supported, try GET with stream
                    if response.status_code == 405:
                        response = requests.get(test_url, timeout=30, stream=True)
                        response.close()
                except requests.exceptions.Timeout:
                    error_message = "Connection timed out after 30 seconds"
                    raise
                
                if response.status_code == 200:
                    success = True
                    # Optional: check Content-Type header
                    content_type = response.headers.get('Content-Type', '')
                    if content_type and 'xml' not in content_type:
                        messages.warning(request, f"Warning: Content-Type is '{content_type}' (expected application/xml or text/xml)")
                else:
                    error_message = f"HTTP {response.status_code}: {response.reason}"
            
            elif source.source_type == 'API' and source.api_endpoint:
                # Test REST API endpoint
                test_url = source.api_endpoint
                try:
                    response = requests.head(test_url, timeout=30, allow_redirects=True)
                    # If HEAD not supported, try GET
                    if response.status_code == 405:
                        response = requests.get(test_url, timeout=30)
                except requests.exceptions.Timeout:
                    error_message = "Connection timed out after 30 seconds"
                    raise
                
                if response.status_code in [200, 201]:
                    success = True
                else:
                    error_message = f"HTTP {response.status_code}: {response.reason}"
            
            else:
                error_message = f"No valid endpoint configured for {source.source_type} source"
        
        except requests.exceptions.Timeout as e:
            if not error_message:
                error_message = f"Connection timed out: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            error_message = f"Connection error: {str(e)}"
        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
        
        # Update source status and show result
        if success:
            source.status = 'active'
            source.save(update_fields=['status'])
            messages.success(
                request,
                f"✅ Connection successful to {test_url}"
            )
        else:
            source.status = 'error'
            source.save(update_fields=['status'])
            messages.error(
                request,
                f"❌ Connection failed: {error_message}<br>Tested URL: {test_url}"
            )
        
        return HttpResponseRedirect(reverse('admin:resources_oersource_changelist'))

    def changelist_view(self, request, extra_context=None):
        """Add KBART upload link to changelist context"""
        extra_context = extra_context or {}
        extra_context['kbart_upload_url'] = reverse('resources:kbart_upload')
        return super().changelist_view(request, extra_context=extra_context)

# ---------------------------------------------------------------------------- #
#                               Harvest Job Admin                              #
# ---------------------------------------------------------------------------- #

@admin.register(HarvestJob)
class HarvestJobAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'source',
        'started_at',
        'status_badge',
        'duration_display',
        'results_summary'
    ]
    
    list_filter = ['status', 'source', 'started_at']
    search_fields = ['source__name', 'error_message']
    readonly_fields = [
        'source',
        'started_at',
        'completed_at',
        'status',
        'resources_found',
        'resources_created',
        'resources_updated',
        'resources_skipped',
        'resources_failed',
        'pages_processed',
        'api_calls_made',
        'error_message',
        'error_details',
        'log_messages',
        'triggered_by'
    ]

    fieldsets = (
        ('Job Information', {
            'fields': ('source', 'started_at', 'completed_at', 'status', 'triggered_by')
        }),
        ('Results', {
            'fields': ('resources_found', 'resources_created', 'resources_updated',
                      'resources_skipped', 'resources_failed')
        }),
        ('Technical Details', {
            'fields': ('pages_processed', 'api_calls_made', 'error_message', 'error_details')
        }),
        ('Logs', {
            'fields': ('log_messages',),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'partial': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px;'
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def duration_display(self, obj):
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}m {seconds}s"
        return mark_safe('<em>In progress...</em>')
    duration_display.short_description = 'Duration'

    def results_summary(self, obj):
        return format_html(
            '<strong>+{}</strong> created, <strong>{}</strong> updated, <em>{}</em> skipped',
            obj.resources_created,
            obj.resources_updated,
            obj.resources_skipped
        )
    results_summary.short_description = 'Results'

    def has_add_permission(self, request):
        return False

# ---------------------------------------------------------------------------- #
#                               OER Resource Admin                             #
# ---------------------------------------------------------------------------- #

@admin.action(description="Enrich metadata for selected resources (AI-assisted)")
def enrich_metadata_action(modeladmin, request, queryset):
    results = metadata_enricher.enrich_queryset(queryset)
    updated = sum(1 for r in results if r.updated_fields)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if r.error)

    msg_parts = []
    if updated:
        msg_parts.append(f"{updated} updated")
    if skipped:
        msg_parts.append(f"{skipped} skipped (already rich metadata)")
    if failed:
        msg_parts.append(f"{failed} failed")

    messages.info(
        request,
        "Metadata enrichment: " + ", ".join(msg_parts) if msg_parts else "No changes made.",
    )

@admin.register(OERResource)
class OERResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'source',
        'publisher',
        'date_first_published',
        'url_display',
        'normalised_type',  # ← CHANGED: was 'resource_type'
        'overall_quality_score',
        'has_embedding',
    ]
    list_filter = [
        'source',
        'normalised_type',  # ← CHANGED: was 'resource_type'
        'is_active',
        'language',
        'date_first_published',
        'overall_quality_score',
    ]
    search_fields = ['title', 'description', 'publisher', 'author']
    readonly_fields = [
        'created_at',
        'updated_at',
        'last_verified',
        'overall_quality_score',
        'embedding_status',
    ]
    list_per_page = 50
    actions = [
        generate_embeddings_action,
        run_quality_assessment_action,
        run_quality_assessment_all_action,
        enrich_metadata_action, 
    ]

    def url_display(self, obj):
        return format_html('<a href="{}" target="_blank">🔗 View</a>', obj.url)
    url_display.short_description = 'URL'

    def has_embedding(self, obj):
        """Display whether resource has an embedding (for list view)."""
        return obj.content_embedding is not None
    has_embedding.boolean = True
    has_embedding.short_description = "Has embedding"

    def embedding_status(self, obj):
        """Display embedding status in the change form (human-readable)."""
        if obj.content_embedding is not None:
            return format_html(
                '<span style="color: green;">✓ Embedding present (384 dimensions)</span>'
            )
        return format_html(
            '<span style="color: orange;">⚠ No embedding</span>'
        )
    embedding_status.short_description = "Embedding status"

    fieldsets = (
        (None, {
            'fields': ('title', 'publisher', 'author', 'source', 'date_first_published')
        }),
        ('Content', {
            'fields': ('description', 'url', 'license', 'normalised_type', 'format')  
        }),
        ('Details', {
            'fields': ('subject', 'level', 'language', 'keywords', 'ai_generated_summary'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'is_active',
                'embedding_status',
                'created_at',
                'updated_at',
                'last_verified',
                'overall_quality_score'
            ),
            'classes': ('collapse',)
        }),
    )

# ---------------------------------------------------------------------------- #
#                               Talis Push Job Admin                           #
# ---------------------------------------------------------------------------- #

@admin.register(TalisPushJob)
class TalisPushJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'target_url', 'created_at', 'started_at', 'completed_at', 'response_code']
