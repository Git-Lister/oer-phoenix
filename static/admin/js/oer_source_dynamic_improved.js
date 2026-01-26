// New supplier-first presets + existing visibility logic for OERSource form

document.addEventListener("DOMContentLoaded", function () {
  const sourceTypeSelect = document.getElementById("id_source_type");

  // ---------------------------------------------------------------------------
  // 1. Existing CONFIG and visibility logic (kept from your current file)
  // ---------------------------------------------------------------------------

  const CONFIG = {
    API: {
      configFields: ["id_api_endpoint", "id_request_headers", "id_request_params"],
      cssClass: "api-config",
    },
    OAIPMH: {
      configFields: ["id_oaipmh_url", "id_oaipmh_set_spec"],
      cssClass: "oaipmh-config",
    },
    CSV: {
      configFields: ["id_csv_url", "id_kbart_file"],
      cssClass: "csv-config",
    },
    MARCXML: {
      configFields: ["id_marcxml_url"],
      cssClass: "marcxml-config",
    },
  };

  function updateFormVisibility(selectedType) {
    // Hide all config sections
    document.querySelectorAll('[class*="-config"]').forEach((section) => {
      section.style.display = "none";
    });

    // Show only the relevant section
    if (selectedType && CONFIG[selectedType]) {
      const cssClass = CONFIG[selectedType].cssClass;
      document.querySelectorAll("." + cssClass).forEach((section) => {
        section.style.display = "block";
      });
    }

    updateFieldRequirements(selectedType);
    filterPresetButtons(selectedType);
  }

  function updateFieldRequirements(sourceType) {
    // Clear all required flags
    document
      .querySelectorAll("input[required], select[required], textarea[required]")
      .forEach((field) => {
        field.required = false;
      });

    // Set required for the selected source type
    if (sourceType && CONFIG[sourceType]) {
      CONFIG[sourceType].configFields.forEach((fieldId) => {
        const field = document.getElementById(fieldId);
        if (field) {
          field.required = true;
        }
      });
    }
  }

  function filterPresetButtons(selectedType) {
    // Legacy preset buttons (if any) – keep behaviour but they may be unused
    document.querySelectorAll(".preset-button[data-type]").forEach((btn) => {
      const btnType = btn.getAttribute("data-type");

      if (selectedType === btnType) {
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.style.cursor = "pointer";
      } else {
        btn.disabled = true;
        btn.style.opacity = "0.45";
        btn.style.cursor = "not-allowed";
      }
    });
  }

  function attachFieldRowClass(fieldId, cssClass) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    let row = field.closest(".form-row") || field.parentElement;
    if (row) {
      row.classList.add(cssClass);
    }
  }

  function initializeFormFields() {
    Object.entries(CONFIG).forEach(([sourceType, config]) => {
      config.configFields.forEach((fieldId) => {
        attachFieldRowClass(fieldId, config.cssClass);
      });
    });
  }

  initializeFormFields();
  if (sourceTypeSelect) {
    updateFormVisibility(sourceTypeSelect.value);
    sourceTypeSelect.addEventListener("change", function () {
      updateFormVisibility(this.value);
    });
  }

  // ---------------------------------------------------------------------------
  // 2. NEW supplier-first preset dropdown behaviour for add_oer_source
  // ---------------------------------------------------------------------------

  if (!window.OER_PRESETS) {
    // No supplier presets JSON injected; nothing more to do.
    return;
  }

  const presetSelect = document.getElementById("id_oer_preset");
  if (!presetSelect) {
    // We are probably on the legacy admin create_source page.
    return;
  }

  const apiField = document.getElementById("id_api_endpoint");
  const oaipmhField = document.getElementById("id_oaipmh_url");
  const csvField = document.getElementById("id_csv_url");
  const marcxmlField = document.getElementById("id_marcxml_url");
  const nameField = document.getElementById("id_name");

  // Populate dropdown with supplier-first presets
  window.OER_PRESETS.forEach(function (preset) {
    const opt = document.createElement("option");
    opt.value = preset.id;
    opt.textContent = preset.label;
    presetSelect.appendChild(opt);
  });

  function clearUrls() {
    if (apiField) apiField.value = "";
    if (oaipmhField) oaipmhField.value = "";
    if (csvField) csvField.value = "";
    if (marcxmlField) marcxmlField.value = "";
  }

  presetSelect.addEventListener("change", function () {
    const chosenId = this.value;
    const chosen = window.OER_PRESETS.find(function (p) {
      return p.id === chosenId;
    });
    if (!chosen) return;

    clearUrls();

    // Set source_type to protocol (API, OAIPMH, CSV, MARCXML)
    if (sourceTypeSelect) {
      sourceTypeSelect.value = chosen.protocol;
      updateFormVisibility(chosen.protocol);
    }

    // Real preset => fill URLs; Custom => leave URLs for manual entry
    if (chosen.preset_key) {
      if (chosen.protocol === "API" && apiField) {
        apiField.value = chosen.api_endpoint || "";
      } else if (chosen.protocol === "OAIPMH" && oaipmhField) {
        oaipmhField.value = chosen.oaipmh_url || "";
      } else if (chosen.protocol === "CSV" && csvField) {
        csvField.value = chosen.csv_url || "";
      } else if (chosen.protocol === "MARCXML" && marcxmlField) {
        marcxmlField.value = chosen.marcxml_url || "";
      }

      if (nameField && !nameField.value) {
        nameField.value = chosen.label;
      }
    } else {
      // Custom presets: just set name if empty, leave URLs to the user
      if (nameField && !nameField.value) {
        nameField.value = chosen.label;
      }
    }
  });

  // Export for debugging if you still need them
  window.updateFormVisibility = updateFormVisibility;
  window.filterPresetButtons = filterPresetButtons;
});
