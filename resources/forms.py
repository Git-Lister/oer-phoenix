from django import forms
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from .models import OERSource, OERResource


class OERSourceForm(forms.ModelForm):
    """Unified form for all OER source types - used in admin"""
    
    class Meta:
        model = OERSource
        fields = [
            'name', 'description', 'source_type', 'is_active', 
            'harvest_schedule', 'max_resources_per_harvest',
            'api_endpoint', 'api_key', 'request_headers', 'request_params',
            'oaipmh_url', 'oaipmh_set_spec', 
            'csv_url',
            'marcxml_url'  # ← ADDED
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make URL fields not required initially - JavaScript will handle this
        self.fields['api_endpoint'].required = False
        self.fields['oaipmh_url'].required = False
        self.fields['csv_url'].required = False
        self.fields['marcxml_url'].required = False  # ← ADDED
        
        # Add URL validators
        url_validator = URLValidator()
        self.fields['api_endpoint'].validators.append(url_validator)
        self.fields['oaipmh_url'].validators.append(url_validator)
        self.fields['marcxml_url'].validators.append(url_validator)  # ← ADDED

        # Optional KBART upload (admin-only non-model field)
        self.fields['kbart_file'] = forms.FileField(
            required=False,
            label=_('KBART file (TSV)'),
            help_text=_('Upload a KBART .tsv file to import directly for CSV/KBART sources')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        
        # Validate based on selected source type
        if source_type == 'API' and not cleaned_data.get('api_endpoint'):
            self.add_error('api_endpoint', 'API endpoint is required for API sources')
        
        elif source_type == 'OAIPMH' and not cleaned_data.get('oaipmh_url'):
            self.add_error('oaipmh_url', 'OAI-PMH URL is required for OAI-PMH sources')
        
        elif source_type == 'CSV':
            # For CSV sources allow either a URL or a KBART file upload (kbart_file)
            csv_url = cleaned_data.get('csv_url')
            kbart_file = cleaned_data.get('kbart_file')
            if not csv_url and not kbart_file:
                self.add_error('csv_url', 'CSV URL or KBART file is required for CSV/KBART sources')
            # If a CSV URL is provided, validate it's a URL here (field-level validators were disabled)
            if csv_url:
                url_validator = URLValidator()
                try:
                    url_validator(csv_url)
                except Exception:
                    self.add_error('csv_url', 'Enter a valid URL.')
        
        # ← ADDED THIS ENTIRE BLOCK
        elif source_type == 'MARCXML':
            marcxml_url = cleaned_data.get('marcxml_url')
            if not marcxml_url:
                self.add_error('marcxml_url', 'MARCXML URL is required for MARCXML sources')
            # Validate MARCXML URL format
            if marcxml_url:
                url_validator = URLValidator()
                try:
                    url_validator(marcxml_url)
                except Exception:
                    self.add_error('marcxml_url', 'Enter a valid URL.')
        
        return cleaned_data


# Keep your existing forms for the non-admin views
class HarvesterTypeForm(forms.Form):
    """Form for selecting harvester type"""
    HARVESTER_CHOICES = [
        ('API', 'API Import'),
        ('OAIPMH', 'OAI-PMH Import'), 
        ('CSV', 'CSV Upload')
    ]
    
    harvester_type = forms.ChoiceField(
        choices=HARVESTER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class BaseHarvesterForm(forms.ModelForm):
    """Base form class for harvester forms"""
    
    class Meta:
        model = OERSource
        fields = ['name', 'description', 'is_active', 'harvest_schedule', 'max_resources_per_harvest']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_default_validators()
        
    def add_default_validators(self):
        """Add common validators to fields"""
        url_fields = ['api_endpoint', 'oaipmh_url', 'csv_url', 'marcxml_url']  # ← ADDED marcxml_url
        for field_name in url_fields:
            if field_name in self.fields:
                self.fields[field_name].validators.append(URLValidator())


class APIHarvesterForm(BaseHarvesterForm):
    """Form for creating/updating an API harvester source"""
    
    class Meta:
        model = OERSource
        fields = BaseHarvesterForm.Meta.fields + ['api_endpoint', 'api_key', 'request_headers', 'request_params']
        
    def clean_api_key(self):
        api_key = self.cleaned_data.get('api_key')
        if api_key and not api_key.replace('_', '').isalnum():
            raise forms.ValidationError(_("API key must contain only letters, numbers, and underscores."))
        return api_key
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = _("Source Name")
        self.fields['api_endpoint'].label = _("API Endpoint")
        self.fields['api_endpoint'].help_text = _("Enter the API URL (e.g., https://example.com/api)")
        # Set initial source_type for new instances
        if not self.instance.pk:
            self.instance.source_type = 'API'


class OAIPMHHarvesterForm(BaseHarvesterForm):
    """Form for creating/updating an OAI-PMH harvester source"""
    
    class Meta:
        model = OERSource
        fields = BaseHarvesterForm.Meta.fields + ['oaipmh_url', 'oaipmh_set_spec']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = _("Source Name")
        self.fields['oaipmh_url'].label = _("OAI-PMH Endpoint")
        self.fields['oaipmh_url'].help_text = _("Enter the OAI-PMH endpoint URL (e.g., https://example.com/oai)")
        self.fields['oaipmh_set_spec'].label = _("Set Specification")
        self.fields['oaipmh_set_spec'].help_text = _("Enter the set specification for this harvest (e.g., 'oer')")
        # Set initial source_type for new instances
        if not self.instance.pk:
            self.instance.source_type = 'OAIPMH'


class CSVHarvesterForm(BaseHarvesterForm):
    """Form for creating/updating a CSV harvester source"""
    
    class Meta:
        model = OERSource
        fields = BaseHarvesterForm.Meta.fields + ['csv_url']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = _("Source Name")
        self.fields['csv_url'].label = _("CSV URL")
        self.fields['csv_url'].help_text = _("Enter the CSV file URL (e.g., https://example.com/data.csv)")
        # Set initial source_type for new instances
        if not self.instance.pk:
            self.instance.source_type = 'CSV'


# Keep your other forms unchanged
class CSVUploadForm(forms.Form):
    """Form for handling CSV file uploads"""
    
    csv_file = forms.FileField(
        label=_("Select a CSV or TSV file"),
        help_text=_("Supported formats: .csv, .tsv")
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if not csv_file.name.lower().endswith(('.csv', '.tsv')):
            raise forms.ValidationError(_("Please upload a CSV or TSV file."))
        return csv_file


class KBARTUploadForm(forms.Form):
    """Form for uploading KBART TSV files or providing a KBART URL."""
    kbart_file = forms.FileField(
        label=_("Upload KBART (TSV) file"),
        required=False,
        help_text=_("Upload a KBART .tsv file")
    )
    kbart_url = forms.URLField(
        label=_("KBART file URL"),
        required=False,
        help_text=_("Or paste a URL to a KBART .tsv file")
    )
    source = forms.ModelChoiceField(
        queryset=OERSource.objects.all(),
        label=_("Attach to source"),
        required=False,
        help_text=_("Choose an existing OER source (or leave blank to create new)")
    )
    create_source_name = forms.CharField(
        label=_("Create source with name"),
        required=False,
        help_text=_("If provided and 'source' is empty, a new OERSource will be created with this name")
    )

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get('kbart_file')
        url = cleaned.get('kbart_url')
        if not file and not url:
            raise forms.ValidationError(_('Please provide a KBART file or URL.'))
        return cleaned


class ExportForm(forms.Form):
    """Form for selecting export format"""
    
    export_type = forms.ChoiceField(
        choices=[
            ('CSV', _('Export as CSV')),
            ('JSON', _('Export as JSON'))
        ],
        widget=forms.RadioSelect,
        label=_("Choose Export Format")
    )


class TalisExportForm(forms.Form):
    """Form for Talis export with resource selection"""
    title = forms.CharField(
        max_length=200,
        required=True,
        label=_("Reading List Title"),
        help_text=_("Enter a title for your Talis reading list")
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label=_("Description (Optional)"),
        help_text=_("Optional description for your reading list")
    )
    resource_ids = forms.ModelMultipleChoiceField(
        queryset=OERResource.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_("Select Resources"),
        help_text=_("Choose which resources to include in the export")
    )
