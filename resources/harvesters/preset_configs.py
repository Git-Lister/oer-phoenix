"""
Preset configurations for common OER sources
====================================================================
LAST VERIFIED: January 14, 2026

This module contains preset configurations for harvesting OER from major
repositories using different protocols (API, OAI-PMH, CSV, MARCXML, KBART).

Each preset is tagged with:
- Content Type: What it harvests (books, chapters, courses, etc.)
- Protocol: How data is retrieved
- Status: Verified working/needs testing
- Resource Level: Granularity of records
"""


class PresetAPIConfigs:
    """
    REST API harvesters for OER repositories
    =========================================
    These use HTTP REST APIs returning JSON responses.
    Generally more flexible than OAI-PMH but less standardized.
    """

    @staticmethod
    def get_oapen_chapters_api_config():
        """
        OAPEN REST API - CHAPTER-LEVEL IMPORT
        ======================================
        #TAG: API_Harvester #Book_Chapters #Open_Access_Content
        #CONTENT: Book chapters from Open Access monographs
        #SUBJECTS: Humanities, Social Sciences, interdisciplinary
        #LANGUAGE: Multilingual (primarily English, German, French, Dutch)
        #STATUS: Verified working (Jan 2026)

        Uses dc.type metadata query to filter for chapter-level records.
        Each record represents a single book chapter with downloadable PDF.
        """
        return {
            "name": "OAPEN REST API (Chapters)",
            "description": "OAPEN REST API filtered to chapter-level records using dc.type metadata.",
            "api_endpoint": "https://library.oapen.org/rest/search",
            "request_params": {
                "query": "dc.type:chapter",
                "expand": "metadata,bitstreams",
            },
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_oapen_books_api_config():
        """
        OAPEN REST API - BOOK-LEVEL IMPORT
        ===================================
        #TAG: API_Harvester #Books #Monographs #Open_Access_Content
        #CONTENT: Complete Open Access books/monographs
        #SUBJECTS: Humanities, Social Sciences, interdisciplinary
        #LANGUAGE: Multilingual (primarily English, German, French, Dutch)
        #STATUS: Verified working (Jan 2026)
        #RESOURCE_TYPE: Book/Monograph (complete works)

        Harvests full book metadata with bitstream links.
        Use this for monograph-level cataloging.
        """
        return {
            "name": "OAPEN REST API (Books)",
            "description": "OAPEN REST API for book-level records with full metadata and bitstreams.",
            "api_endpoint": "https://library.oapen.org/rest/search",
            "request_params": {
                "query": "*",
                "expand": "metadata,bitstreams",
            },
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_doab_api_config():
        """
        Directory of Open Access Books - REST API
        ==========================================
        #TAG: API_Harvester #Books #Monographs #Open_Access_Directory
        #CONTENT: Open Access book metadata (directory/catalog)
        #SUBJECTS: All academic disciplines
        #LANGUAGE: Multilingual
        #STATUS: Verified working (Jan 2026)
        #RESOURCE_TYPE: Book/Monograph
        #NOTE: DOAB is an aggregator - provides metadata only, not full text

        DOAB aggregates OA books from multiple publishers.
        Metadata describes books, but full text is on publisher sites.
        """
        return {
            "name": "DOAB REST API",
            "description": "Directory of Open Access Books via REST API",
            "api_endpoint": "https://directory.doabooks.org/rest/search",
            "request_params": {"query": "*", "expand": "metadata,bitstreams"},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 2000,
        }

    # UNVERIFIED/EXPERIMENTAL – kept for reference but not exposed via SUPPLIER_PRESETS

    @staticmethod
    def get_merlot_api_config():
        """
        MERLOT - Learning Objects Repository (UNVERIFIED)
        """
        return {
            "name": "MERLOT API (UNVERIFIED)",
            "description": "MERLOT OER Repository API (UNVERIFIED)",
            "api_endpoint": "https://api.merlot.org/materials",
            "request_params": {"format": "json", "per_page": 100},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 500,
        }

    @staticmethod
    def get_openstax_api_config():
        """
        OpenStax - Open Textbooks API (NEEDS VERIFICATION)
        """
        return {
            "name": "OpenStax API (NEEDS VERIFICATION)",
            "description": "OpenStax OER Textbooks API (NEEDS VERIFICATION)",
            "api_endpoint": "https://openstax.org/api/v2/pages",
            "request_params": {"type": "books.Book", "fields": "*"},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 100,
        }


class PresetOAIPMHConfigs:
    """
    OAI-PMH protocol harvesters
    ============================
    OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting)
    is a standardized protocol for harvesting metadata from digital repositories.

    Unlike REST APIs, OAI-PMH is specifically designed for library/repository
    interoperability and uses Dublin Core metadata as its base format.

    NOTE: OAPEN and DOAB OAI-PMH endpoints are currently broken.
    Use KBART/MARCXML/REST API alternatives instead.
    """

    @staticmethod
    def get_skills_commons_oaipmh_config():
        """
        Skills Commons - Workforce Training OER Repository
        ===================================================
        #TAG: OAI-PMH_Harvester #Workforce_Training #Career_Technical_Education
        #CONTENT: Job training materials, workforce development resources
        #STATUS: ✅ VERIFIED WORKING (Jan 14, 2026)
        """
        return {
            "name": "Skills Commons OER (OAI-PMH) ✅",
            "description": "Skills Commons workforce training OER via OAI-PMH",
            "oaipmh_url": "https://library.skillscommons.org/server/oai/request",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 10000,
        }

    # NOT RESPONDING – kept for reference, not wired into SUPPLIER_PRESETS

    @staticmethod
    def get_mit_oaipmh_config():
        """
        MIT OpenCourseWare - OAI-PMH ENDPOINT (NOT RESPONDING)
        """
        return {
            "name": "MIT OpenCourseWare (OAI-PMH) ⚠️",
            "description": "MIT OpenCourseWare - ENDPOINT NOT RESPONDING",
            "oaipmh_url": "https://ocw.mit.edu/oaipmh",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_oe_global_oaipmh_config():
        """
        Open Education Global Repository - OAI-PMH ENDPOINT (NOT RESPONDING)
        """
        return {
            "name": "OE Global Repository (OAI-PMH) ⚠️",
            "description": "Open Education Global - NEEDS VERIFICATION",
            "oaipmh_url": "https://repository.oeglobal.org/oai/request",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 2000,
        }


class PresetCSVConfigs:
    """
    CSV/TSV/KBART-based harvesters
    ===============================
    These presets harvest from CSV, TSV (tab-separated), or KBART data exports.
    """

    @staticmethod
    def get_oapen_kbart_config():
        """
        OAPEN Library - KBART Books Export
        ====================================
        #TAG: KBART_Harvester #Books #Tab_Separated #WORKING
        #STATUS: ✅ VERIFIED WORKING (Jan 14, 2026)
        """
        return {
            "name": "OAPEN Library (KBART) ✅ RECOMMENDED",
            "description": "OAPEN books via KBART format - WORKING alternative to broken OAI-PMH",
            "csv_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_KBART_books.tsv",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_oer_commons_csv_config():
        """
        OER Commons - CSV Export (UNVERIFIED)
        """
        return {
            "name": "OER Commons CSV (UNVERIFIED)",
            "description": "OER Commons resource catalog via CSV (NEEDS VERIFICATION)",
            "csv_url": "https://www.oercommons.org/export/csv",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "monthly",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_skills_commons_csv_config():
        """
        Skills Commons - CSV Export (UNVERIFIED)
        """
        return {
            "name": "Skills Commons CSV (UNVERIFIED)",
            "description": "Skills Commons OER materials catalog (CSV) - UNVERIFIED",
            "csv_url": "https://www.skillscommons.org/export/oer.csv",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "monthly",
            "max_resources_per_harvest": 10000,
        }

    @staticmethod
    def get_kbart_tsv_config():
        """
        KBART Format Import - Generic Template
        ========================================
        """
        return {
            "name": "KBART (TSV) Import - Generic",
            "description": "KBART-compliant TSV listing of serials/works; upload or provide URL to import.",
            "csv_url": "",  # Provided by user when creating source
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 10000,
        }


# =============================================================================
# COMBINED PRESET REGISTRY
# =============================================================================

PRESET_CONFIGS = {
    "API": {
        "oapen_books": PresetAPIConfigs.get_oapen_books_api_config(),
        "oapen_chapters": PresetAPIConfigs.get_oapen_chapters_api_config(),
        "doab": PresetAPIConfigs.get_doab_api_config(),
        # "merlot": PresetAPIConfigs.get_merlot_api_config(),       # UNVERIFIED - hidden
        # "openstax": PresetAPIConfigs.get_openstax_api_config(),   # UNVERIFIED - hidden
    },
    "OAIPMH": {
        # OAPEN and DOAB OAI-PMH endpoints are broken; do not expose here
        "skills_commons": PresetOAIPMHConfigs.get_skills_commons_oaipmh_config(),
        # "mit": PresetOAIPMHConfigs.get_mit_oaipmh_config(),       # NOT RESPONDING - hidden
        # "oe_global": PresetOAIPMHConfigs.get_oe_global_oaipmh_config(),  # NOT RESPONDING - hidden
    },
    "CSV": {
        "oapen_kbart": PresetCSVConfigs.get_oapen_kbart_config(),  # ⭐ RECOMMENDED for OAPEN
        # "oer_commons": PresetCSVConfigs.get_oer_commons_csv_config(),      # UNVERIFIED - hidden
        # "skills_commons_csv": PresetCSVConfigs.get_skills_commons_csv_config(),  # UNVERIFIED - hidden
        "kbart_generic": PresetCSVConfigs.get_kbart_tsv_config(),
    },
    "MARCXML": {
        # Kept as placeholders; fill with real MARCXML configs as needed
        "oapen": {
            "name": "OAPEN MARCXML (Books)",
            "description": "OAPEN books via MARCXML export.",
            "marcxml_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_books.xml",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        },
        "oapen_chapters": {
            "name": "OAPEN MARCXML (Chapters)",
            "description": "OAPEN chapters via MARCXML export.",
            "marcxml_url": "",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        },
        "doab": {
            "name": "DOAB MARCXML",
            "description": "DOAB MARCXML export (endpoint to be configured).",
            "marcxml_url": "",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        },
    },
}


# =============================================================================
# SUPPLIER-FIRST PRESET REGISTRY (for UI)
# =============================================================================

SUPPLIER_PRESETS = {
    # OAPEN – REST API (Books/Chapters)
    "oapen_books_api": {
        "label": "OAPEN – Books – API",
        "supplier": "OAPEN",
        "content_scope": "Books",
        "protocol": "API",
        "preset_key": "oapen_books",   # PRESET_CONFIGS["API"]
    },
    "oapen_chapters_api": {
        "label": "OAPEN – Chapters – API",
        "supplier": "OAPEN",
        "content_scope": "Chapters",
        "protocol": "API",
        "preset_key": "oapen_chapters",
    },

    # DOAB – REST API
    "doab_books_api": {
        "label": "DOAB – Books – API",
        "supplier": "DOAB",
        "content_scope": "Books",
        "protocol": "API",
        "preset_key": "doab",
    },

    # Skills Commons – OAI-PMH (working)
    "skills_commons_oaipmh": {
        "label": "Skills Commons – Various – OAI-PMH",
        "supplier": "Skills Commons",
        "content_scope": "Various",
        "protocol": "OAIPMH",
        "preset_key": "skills_commons",
    },

    # Generic KBART – CSV (working)
    "generic_kbart": {
        "label": "Generic – KBART (TSV) Import",
        "supplier": "Generic",
        "content_scope": "KBART holdings",
        "protocol": "CSV",
        "preset_key": "kbart_generic",
    },

    # Custom – manual presets
    "custom_api": {
        "label": "Custom – API (manual configuration)",
        "supplier": "Custom",
        "content_scope": "Manual",
        "protocol": "API",
        "preset_key": None,
    },
    "custom_oaipmh": {
        "label": "Custom – OAI-PMH (manual configuration)",
        "supplier": "Custom",
        "content_scope": "Manual",
        "protocol": "OAIPMH",
        "preset_key": None,
    },
    "custom_marcxml": {
        "label": "Custom – MARCXML (manual configuration)",
        "supplier": "Custom",
        "content_scope": "Manual",
        "protocol": "MARCXML",
        "preset_key": None,
    },
    "custom_csv": {
        "label": "Custom – CSV / KBART (manual configuration)",
        "supplier": "Custom",
        "content_scope": "Manual",
        "protocol": "CSV",
        "preset_key": None,
    },
}
