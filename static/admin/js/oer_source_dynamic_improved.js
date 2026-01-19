// Simplified and improved oer_source_dynamic.js
// Purpose: Handle dynamic form visibility and preset filtering based on source type

document.addEventListener('DOMContentLoaded', function() {
    const sourceTypeSelect = document.getElementById('id_source_type');
    
    // Configuration mapping source types to their form sections
    const CONFIG = {
        'API': {
            configFields: ['id_api_endpoint', 'id_request_headers', 'id_request_params'],
            cssClass: 'api-config'
        },
        'OAIPMH': {
            configFields: ['id_oaipmh_url', 'id_oaipmh_set_spec'],
            cssClass: 'oaipmh-config'
        },
        'CSV': {
            configFields: ['id_csv_url', 'id_kbart_file'],
            cssClass: 'csv-config'
        },
        'MARCXML': {
            configFields: ['id_marcxml_url'],
            cssClass: 'marcxml-config'
        }
    };

    /**
     * Show/hide form sections based on selected source type
     */
    function updateFormVisibility(selectedType) {
        // Hide all config sections
        document.querySelectorAll('[class*="-config"]').forEach(section => {
            section.style.display = 'none';
        });

        // Show only the relevant section
        if (selectedType && CONFIG[selectedType]) {
            const cssClass = CONFIG[selectedType].cssClass;
            document.querySelectorAll(`.${cssClass}`).forEach(section => {
                section.style.display = 'block';
            });
        }

        updateFieldRequirements(selectedType);
        filterPresetButtons(selectedType);
    }

    /**
     * Set field requirements based on source type
     */
    function updateFieldRequirements(sourceType) {
        // Clear all required flags
        document.querySelectorAll('input[required], select[required], textarea[required]').forEach(field => {
            field.required = false;
        });

        // Set required for the selected source type
        if (sourceType && CONFIG[sourceType]) {
            CONFIG[sourceType].configFields.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (field) {
                    field.required = true;
                }
            });
        }
    }

    /**
     * Enable/disable preset buttons based on selected source type
     */
    function filterPresetButtons(selectedType) {
        document.querySelectorAll('.preset-button[data-type]').forEach(btn => {
            const btnType = btn.getAttribute('data-type');
            
            if (selectedType === btnType) {
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            } else {
                btn.disabled = true;
                btn.style.opacity = '0.45';
                btn.style.cursor = 'not-allowed';
            }
        });
    }

    /**
     * Attach CSS class to form field rows for visibility toggling
     */
    function attachFieldRowClass(fieldId, cssClass) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        // Find the containing form row (Django admin structure)
        let row = field.closest('.form-row') || field.parentElement;
        if (row) {
            row.classList.add(cssClass);
        }
    }

    /**
     * Initialize: attach CSS classes to all form fields
     */
    function initializeFormFields() {
        Object.entries(CONFIG).forEach(([sourceType, config]) => {
            config.configFields.forEach(fieldId => {
                attachFieldRowClass(fieldId, config.cssClass);
            });
        });
    }

    // Initialize on load
    initializeFormFields();
    if (sourceTypeSelect) {
        updateFormVisibility(sourceTypeSelect.value);
        sourceTypeSelect.addEventListener('change', function() {
            updateFormVisibility(this.value);
        });
    }

    // Export functions globally for testing/debugging
    window.updateFormVisibility = updateFormVisibility;
    window.filterPresetButtons = filterPresetButtons;
});
