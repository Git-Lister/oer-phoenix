"""
Preset configurations for common OER sources
Updated with robust OAPEN/DOAB REST API presets.
"""


class PresetAPIConfigs:
    """Preset configurations for API harvesters"""

    @staticmethod
    def get_oapen_chapters_api_config():
        """
        OAPEN REST API preset targeting chapters.

        Uses a metadata query on dc.type to bias towards chapter-level records.
        Adjust the query if OAPEN refines their chapter typing.
        """
        return {
            "name": "OAPEN REST API (Chapters)",
            "description": "OAPEN REST API filtered to chapter-level records "
                           "using dc.type metadata.",
            "api_endpoint": "https://library.oapen.org/rest/search",
            # Query syntax per OAPEN REST docs: ?query=[search query]
            # Here we request records where dc.type contains 'chapter'
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
        OAPEN REST API preset targeting book-level records.

        Uses a broad full-text query and relies on downstream normalisation
        (e.g. _normalise_resource_type) plus resource-type facets/filters.
        """
        return {
            "name": "OAPEN REST API (Books)",
            "description": "OAPEN REST API for book-level records "
                           "with full metadata and bitstreams.",
            "api_endpoint": "https://library.oapen.org/rest/search",
            "request_params": {
                # '*' → all records; you can later constrain by publisher,
                # classification, or other dc.* fields if needed.
                "query": "*",
                "expand": "metadata,bitstreams",
            },
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_doab_api_config():
        """Directory of Open Access Books API"""
        return {
            "name": "DOAB REST API",
            "description": "Directory of Open Access Books via REST API",
            "api_endpoint": "https://directory.doabooks.org/rest/search",
            "request_params": {"query": "*", "expand": "metadata,bitstreams"},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_merlot_api_config():
        """MERLOT OER Repository API"""
        return {
            "name": "MERLOT API",
            "description": "MERLOT OER Repository API",
            "api_endpoint": "https://api.merlot.org/materials",
            "request_params": {"format": "json", "per_page": 100},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 500,
        }

    @staticmethod
    def get_openstax_api_config():
        """OpenStax OER Textbooks API"""
        return {
            "name": "OpenStax API",
            "description": "OpenStax OER Textbooks API",
            "api_endpoint": "https://openstax.org/api/v2/pages",
            "request_params": {"type": "books.Book", "fields": "*"},
            "request_headers": {"Accept": "application/json"},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 100,
        }


class PresetOAIPMHConfigs:
    """Preset configurations for OAI-PMH harvesters"""

    @staticmethod
    def get_oapen_oaipmh_config():
        """OAPEN Library OAI-PMH (books)"""
        return {
            "name": "OAPEN Library (OAI-PMH) - OER Books",
            "description": "Harvest open access books from OAPEN via OAI-PMH",
            "oaipmh_url": "https://directory.doabooks.org/oai",
            # you can set a books-only setSpec here if needed
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "daily",
            "max_resources_per_harvest": 1000,
        }

    @staticmethod
    def get_doab_oaipmh_config():
        """Directory of Open Access Books OAI-PMH"""
        return {
            "name": "DOAB (OAI-PMH)",
            "description": "Directory of Open Access Books via OAI-PMH",
            "oaipmh_url": "https://www.doabooks.org/oaipmh",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "daily",
            "max_resources_per_harvest": 1000,
        }

    @staticmethod
    def get_mit_oaipmh_config():
        """MIT OpenCourseWare OAI-PMH"""
        return {
            "name": "MIT OpenCourseWare (OAI-PMH)",
            "description": "MIT OpenCourseWare OER materials",
            "oaipmh_url": "https://ocw.mit.edu/oaipmh",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_oe_global_oaipmh_config():
        """OE Global OAI-PMH"""
        return {
            "name": "OE Global Repository (OAI-PMH)",
            "description": "Open Education Global OER repository",
            "oaipmh_url": "https://repository.oeglobal.org/oai/request",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_skills_commons_oaipmh_config():
        """Skills Commons OAI-PMH (per SkillsCommons docs)"""
        return {
            "name": "Skills Commons OER OAI-PMH",
            "description": "Skills Commons OER via OAI-PMH",
            # base endpoint from SkillsCommons OAI docs
            "oaipmh_url": "https://www.skillscommons.org/oai/request",
            # you can plug a specific setSpec if you want (e.g. 'publication:OER')
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 10000,
        }


class PresetCSVConfigs:
    """Preset configurations for CSV sources"""

    @staticmethod
    def get_oer_commons_csv_config():
        """OER Commons CSV export"""
        return {
            "name": "OER Commons CSV",
            "description": "OER Commons resource catalog via CSV",
            "csv_url": "https://www.oercommons.org/export/csv",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "monthly",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_skills_commons_csv_config():
        """Skills Commons OER CSV (if/when available)"""
        return {
            "name": "Skills Commons OER CSV",
            "description": "Skills Commons OER materials catalog (CSV)",
            "csv_url": "https://www.skillscommons.org/export/oer.csv",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "monthly",
            "max_resources_per_harvest": 10000,
        }

    @staticmethod
    def get_kbart_tsv_config():
        """KBART (TSV) import preset - used for publisher KBART files and similar exports."""
        return {
            "name": "KBART (TSV)",
            "description": "KBART-compliant TSV listing of serials/works; upload or provide URL to import.",
            # csv_url can be provided by user when creating source from preset
            "csv_url": "",
            "request_params": {},
            "request_headers": {},
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 10000,
        }


# Combined preset registry for easy access
PRESET_CONFIGS = {
    "API": {
        # Books-only preset
        "oapen_books": PresetAPIConfigs.get_oapen_books_api_config(),
        # Chapters-only preset
        "oapen_chapters": PresetAPIConfigs.get_oapen_chapters_api_config(),
        "doab": PresetAPIConfigs.get_doab_api_config(),
        "merlot": PresetAPIConfigs.get_merlot_api_config(),
        "openstax": PresetAPIConfigs.get_openstax_api_config(),
    },
    "OAIPMH": {
        "oapen": PresetOAIPMHConfigs.get_oapen_oaipmh_config(),
        "doab": PresetOAIPMHConfigs.get_doab_oaipmh_config(),
        "mit": PresetOAIPMHConfigs.get_mit_oaipmh_config(),
        "oe_global": PresetOAIPMHConfigs.get_oe_global_oaipmh_config(),
        "skills_commons": PresetOAIPMHConfigs.get_skills_commons_oaipmh_config(),
    },
    "CSV": {
        "oer_commons": PresetCSVConfigs.get_oer_commons_csv_config(),
        "skills_commons": PresetCSVConfigs.get_skills_commons_csv_config(),
        "kbart": PresetCSVConfigs.get_kbart_tsv_config(),
    },
}

# MARCXML presets - allow admins to add MARCXML/dump-based sources
PRESET_CONFIGS["MARCXML"] = {
    "oapen": {
        "name": "OAPEN MARCXML dump",
        "description": (
            "OAPEN MARCXML dump (books). Uses the OAPEN public MARCXML dump URL."
        ),
        "marcxml_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_books.xml",
        "harvest_schedule": "manual",
        "max_resources_per_harvest": 1000,
    },
    "doab": {
        "name": "DOAB MARCXML dump",
        "description": (
            "DOAB MARCXML export. Update URL if DOAB changes its MARCXML endpoint."
        ),
        "marcxml_url": "https://directory.doabooks.org/metadata/marcxml",
        "harvest_schedule": "manual",
        "max_resources_per_harvest": 1000,
    },
}

