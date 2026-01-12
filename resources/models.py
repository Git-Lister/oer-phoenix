# models.py
"""
OER Source Management Models
Dynamic configuration for OER API sources with admin interface
"""


from django.db import models
from django.core.validators import URLValidator
from django.utils import timezone
from pgvector.django import VectorField
import json


class OERSource(models.Model):
    """
    Configuration for external OER API sources
    Allows dynamic addition of new sources through admin interface
    """
    # Harvester Type - FIXED CHOICES
    SOURCE_TYPES = [
        ('API', 'API Harvester'),
        ('OAIPMH', 'OAI-PMH Harvester'),
        ('CSV', 'CSV Harvester'),
        ('MARCXML', 'MARCXML Harvester'),
    ]
    
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default='API',
        help_text="Select the type of harvester to use for this source"
    )
    
    # Basic Information
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    # NEW: User-friendly display name
    display_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="User-friendly display name (e.g., 'OAPEN Open Access Books' instead of 'OAPEN MARCXML dump')"
    )
    
    # API Configuration
    api_endpoint = models.URLField(
        blank=True,
        null=True,
        help_text="API endpoint URL (e.g., https://example.com/api/v1/resources)"
    )
    api_key = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="API key if required (stored securely)"
    )
    request_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"Authorization": "Bearer token", "Accept": "application/json"}'
    )
    request_params = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"format": "json", "per_page": 100}'
    )
    
    # OAI-PMH Configuration
    oaipmh_url = models.URLField(
        blank=True,
        null=True,
        help_text="OAI-PMH URL (e.g., https://example.com/oai)"
    )
    oaipmh_set_spec = models.CharField(
        max_length=200,
        blank=True,
        help_text="Set specification for the OAI-PMH harvest"
    )
    
    # CSV Configuration
    csv_url = models.URLField(
        blank=True,
        null=True,
        help_text="CSV file URL for CSV harvesting"
    )

    # MARCXML Configuration
    marcxml_url = models.URLField(
        blank=True,
        null=True,
        help_text="MARCXML file URL for MARCXML harvesting (or dump URL)"
    )
    
    # Field Mappings
    field_mappings = models.ManyToManyField(
        'OERSourceFieldMapping',
        related_name='sources',
        blank=True,
        help_text="Map API fields to OER model fields"
    )
    
    # Harvesting Configuration
    is_active = models.BooleanField(default=True)
    harvest_schedule = models.CharField(
        max_length=50,
        default='daily',
        choices=[
            ('manual', 'Manual Only'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ]
    )
    max_resources_per_harvest = models.IntegerField(
        default=1000,
        help_text="Maximum resources to fetch per harvest (0 = unlimited)"
    )
    
    # Status & Tracking
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
        ('error', 'Error'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    last_harvest_at = models.DateTimeField(null=True, blank=True)
    total_harvested = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "OER Source"
        verbose_name_plural = "OER Sources"
        ordering = ['display_name', 'name']  # Updated to prioritize display_name
    
    def __str__(self):
        return f"{self.get_display_name()} ({self.get_status_display()})"
    
    def get_display_name(self):
        """Return display_name if set, otherwise fall back to name"""
        return self.display_name if self.display_name else self.name


class OERResource(models.Model):
    """
    Educational resources fetched from various OER sources
    """
    # Basic Information
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=500)
    source = models.ForeignKey('OERSource', on_delete=models.CASCADE, related_name='resources')
    
    # Resource Details
    license = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=200, blank=True)

    # NEW: richer subject fields
    subjects_raw = models.JSONField(
        default=list,
        blank=True,
        help_text="All subject strings from source metadata."
    )
    ai_subjects = models.JSONField(
        default=list,
        blank=True,
        help_text="AI-suggested subject labels."
    )
    primary_subject = models.CharField(
        max_length=100,
        blank=True,
        help_text="Preferred subject (source or AI-enriched)."
    )

    level = models.CharField(max_length=100, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    author = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=50, blank=True, default='en')
    
    # Resource Type and Format
    resource_type = models.CharField(max_length=100, blank=True)
    format = models.CharField(max_length=100, blank=True)

    RESOURCE_TYPE_CHOICES = [
        ("book", "Book / Monograph"),
        ("chapter", "Book Chapter"),
        ("article", "Article"),
        ("video", "Video"),
        ("course", "Course / Module"),
        ("other", "Other"),
    ]
    normalised_type = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        choices=RESOURCE_TYPE_CHOICES,
        help_text="Normalised internal type derived from source metadata."
    )

    # AI/ML Fields
    content_embedding = VectorField(dimensions=384, null=True, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    ai_generated_summary = models.TextField(blank=True)

    # Extracted content (for LLM/enrichment)
    extracted_text = models.TextField(blank=True, null=True, help_text="Normalized extracted text from linked PDF or webpage")
    content_hash = models.CharField(max_length=64, blank=True, db_index=True, help_text="Hash of downloaded content to avoid re-processing")
    extracted_at = models.DateTimeField(null=True, blank=True, help_text="When content was extracted")
    CONTENT_SOURCE_CHOICES = [
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('other', 'Other'),
    ]
    content_source_type = models.CharField(max_length=20, choices=CONTENT_SOURCE_CHOICES, blank=True, help_text="Detected content type for extracted_text")

    # Standard identifiers
    isbn = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Normalised ISBN-10 or ISBN-13 without punctuation."
    )
    issn = models.CharField(
        max_length=16,
        blank=True,
        db_index=True,
        help_text="Normalised ISSN without punctuation."
    )
    oclc_number = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="OCLC control number (normalised digits only where possible)."
    )
    doi = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="DOI string as provided (not URL)."
    )
    publication_year = models.CharField(
    max_length=4,
    blank=True,
    db_index=True,
    help_text="Year of publication (YYYY format)"
    )
    # NEW: Date fields for resources with online issue dates
    date_first_issue_online = models.CharField(
        max_length=10,
        blank=True,
        help_text="First available online date (YYYY-MM-DD)"
    )
    date_last_issue_online = models.CharField(
        max_length=10,
        blank=True,
        help_text="Last available online date (YYYY-MM-DD)"
    )
# NEW: Volume and issue numbers for serial publications
    num_first_vol_online = models.CharField(
    max_length=50,
    blank=True,
    help_text="First volume number available"
    )
    num_first_issue_online = models.CharField(
        max_length=50,
        blank=True,
        help_text="First issue number available"
    )
    # NEW: Coverage notes from KBART or source metadata
    coverage_notes = models.TextField(
    blank=True,
    help_text="Coverage statement or notes from KBART"
    )
    # NEW: Embargo information field
    embargo_info = models.CharField(
    max_length=200,
    blank=True,
    help_text="Embargo or access restriction info"
    )


    # NEW: Translation fields for non-English resources
    title_en = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="English translation of title (auto-generated during harvest)"
    )
    description_en = models.TextField(
        blank=True,
        null=True,
        help_text="English translation of description (auto-generated during harvest)"
    )

    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Quality Assessment Fields (Phase 1: Evidence-Based, Transparent)
    # Legacy field - kept for backwards compatibility with existing assessment service
    overall_quality_score = models.FloatField(
        default=0.0, 
        db_index=True,
        help_text="Legacy quality score (0-5 scale) - being phased out"
    )
    
    # Phase 1: Objective Metadata Completeness
    metadata_quality_score = models.FloatField(
        default=0.0,
        help_text="Metadata completeness 0-1 (factual, not subjective quality)"
    )
    readiness_for_review = models.BooleanField(
        default=False,
        help_text="Has sufficient metadata for AI/human quality review (≥70% complete)"
    )
    
    # Phase 1: Transparent Trust Signals (factual indicators, not scores)
    trust_signals = models.JSONField(
        default=dict,
        blank=True,
        help_text="Factual trust indicators: from_curated_collection, open_license, updated_recently, etc."
    )
    
    # Phase 2: AI Pedagogical Assessment (future)
    ai_pedagogy_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI pedagogical assessment scores (clarity, objectives, practice, etc.)"
    )
    ai_review_summary = models.TextField(
        blank=True,
        help_text="AI-generated teaching utility summary"
    )
    ai_review_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence in AI review 0-1"
    )
    
    class Meta:
        verbose_name = "OER Resource"
        verbose_name_plural = "OER Resources"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["title", "source"]),
            models.Index(fields=["resource_type", "language"]),
            models.Index(fields=["normalised_type", "language"]),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.source.get_display_name()})"
    
    def get_title_display(self, prefer_english=False):
        """Return appropriate title based on language preference"""
        if prefer_english and self.language != 'en' and self.title_en:
            return self.title_en
        return self.title
    
    def get_description_display(self, prefer_english=False):
        """Return appropriate description based on language preference"""
        if prefer_english and self.language != 'en' and self.description_en:
            return self.description_en
        return self.description
    
    def needs_translation(self):
        """Check if resource needs translation"""
        return self.language and self.language != 'en' and not self.title_en
    
    def is_non_english(self):
        """Check if resource is in a language other than English"""
        return self.language and self.language != 'en'


class OERSourceFieldMapping(models.Model):
    """
    Detailed field mapping configuration for complex API responses
    Allows multiple mapping rules per source
    """
    
    # Source Field Configuration
    source_field_path = models.CharField(
        max_length=300,
        help_text="JSON path in API response (e.g., 'data.attributes.title')"
    )
    
    # Target Field Configuration
    target_model_fields = models.JSONField(
        default=dict,
        help_text='{"OERResource": {"title": "data.title", "description": "data.description"}}'
    )
    
    # Transformation Rules
    is_required = models.BooleanField(default=False)
    default_value = models.CharField(max_length=500, blank=True)
    transformation_rule = models.CharField(
        max_length=50,
        default='direct',
        choices=[
            ('direct', 'Direct Copy'),
            ('lowercase', 'Convert to Lowercase'),
            ('uppercase', 'Convert to Uppercase'),
            ('strip_html', 'Strip HTML Tags'),
            ('join_list', 'Join List with Comma'),
            ('first_item', 'Take First Item from List'),
            ('custom', 'Custom Transformation'),
        ]
    )
    
    # Custom Transformation
    custom_transformation = models.TextField(
        blank=True,
        help_text="Python code for custom transformation (e.g., lambda x: x.upper())"
    )
    
    class Meta:
        verbose_name = "Field Mapping"
        verbose_name_plural = "Field Mappings"
        ordering = ['-is_required', 'target_model_fields']
    
    def __str__(self):
        return f"{self.source_field_path} → {list(self.target_model_fields.keys())[0]}"


class HarvestJob(models.Model):
    """
    Represents a harvesting job for an OER source.
    Tracks the status and results of each harvesting attempt.
    """
    source = models.ForeignKey('OERSource', on_delete=models.CASCADE, related_name='harvest_jobs')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('partial', 'Partial'),
        ],
        default='pending'
    )
    
    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Resource counts
    resources_found = models.IntegerField(default=0)
    resources_created = models.IntegerField(default=0)
    resources_updated = models.IntegerField(default=0)
    resources_skipped = models.IntegerField(default=0)
    resources_failed = models.IntegerField(default=0)
    
    # Technical details
    pages_processed = models.IntegerField(default=0)
    api_calls_made = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    log_messages = models.JSONField(default=list, blank=True)
    
    # Metadata
    triggered_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Harvest Job"
        verbose_name_plural = "Harvest Jobs"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Harvest job for {self.source.get_display_name()} ({self.get_status_display()})"
    
    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def total_resources_harvested(self):
        return self.resources_created + self.resources_updated


class TalisPushJob(models.Model):
    """Tracks asynchronous pushes of AI reports to Talis (or other endpoints)."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    target_url = models.URLField(blank=True, null=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    report_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Talis Push Job"
        verbose_name_plural = "Talis Push Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"TalisPushJob {self.id} ({self.get_status_display()})"
