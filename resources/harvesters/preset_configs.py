"""
Preset configurations for common OER sources
====================================================================
LAST VERIFIED: January 2026

This module contains preset configurations for harvesting OER from major
repositories using different protocols (API, OAI-PMH, CSV, MARCXML).

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

    @staticmethod
    def get_merlot_api_config():
        """
        MERLOT - Learning Objects Repository
        =====================================
        #TAG: API_Harvester #Learning_Objects #Course_Materials #K12_Higher_Ed
        #CONTENT: Peer-reviewed learning materials, exercises, simulations
        #SUBJECTS: All disciplines (organized by discipline communities)
        #LANGUAGE: Primarily English
        #STATUS: UNVERIFIED - No public API documentation found (Jan 2026)
        #RESOURCE_TYPE: Learning Object, Exercise, Simulation, Tool
        #WARNING: This endpoint may not exist or may require authentication
        
        MERLOT contains 91,000+ learning materials across 22 categories.
        Materials are peer-reviewed by discipline-specific communities.
        
        **IMPORTANT**: This preset requires verification. MERLOT may not
        offer a public REST API. Consider using CSV export or web scraping instead.
        """
        return {
            "name": "MERLOT API",
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
        OpenStax - Open Textbooks API
        ==============================
        #TAG: API_Harvester #Textbooks #Higher_Education #K12
        #CONTENT: Peer-reviewed, openly licensed college textbooks
        #SUBJECTS: STEM, Business, Humanities, Social Sciences
        #LANGUAGE: English (some translations available)
        #STATUS: NEEDS VERIFICATION - Endpoint structure uncertain (Jan 2026)
        #RESOURCE_TYPE: Textbook (complete, course-ready textbooks)
        #FORMATS: PDF, HTML, editable formats
        
        OpenStax provides ~50 high-quality textbooks covering major college courses.
        All books are peer-reviewed and professionally designed.
        
        **NOTE**: This endpoint may need adjustment. OpenStax likely requires
        different API access patterns. Verify before use.
        """
        return {
            "name": "OpenStax API",
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
    
    KEY DIFFERENCES FROM APIs:
    - Standardized XML-based protocol
    - Mandatory Dublin Core support
    - Built-in resumption tokens for large harvests
    - Set-based selective harvesting
    - Datestamp-based incremental updates
    """

    @staticmethod
    def get_oapen_oaipmh_config():
        """
        OAPEN Library - OAI-PMH ENDPOINT
        ==================================
        #TAG: OAI-PMH_Harvester #Books_AND_Chapters #Open_Access_Content
        #CONTENT: Books and chapters from Open Access monographs
        #SUBJECTS: Humanities, Social Sciences, interdisciplinary
        #LANGUAGE: Multilingual (primarily English, German, French, Dutch)
        #STATUS: VERIFIED WORKING ✓ (Tested Jan 14, 2026)
        #RESOURCE_TYPE: Book AND Chapter (mixed granularity)
        #METADATA_FORMAT: oai_dc (Dublin Core), xoai (extended)
        
        **VERIFIED**: https://library.oapen.org/oai/request responds correctly
        to OAI-PMH Identify verb with valid OAI 2.0 protocol.
        
        This endpoint provides BOTH book-level and chapter-level records.
        Use _normalise_resource_type() in harvester to distinguish between them.
        
        OAPEN contains peer-reviewed Open Access monographs with full-text PDFs.
        All content is freely downloadable under open licenses (CC-BY, CC BY-NC, etc.)
        """
        return {
            "name": "OAPEN Library (OAI-PMH) - Books & Chapters",
            "description": "Harvest open access books AND chapters from OAPEN via OAI-PMH",
            "oaipmh_url": "https://library.oapen.org/oai/request",  # CORRECTED
            "oaipmh_set_spec": "",  # Empty = harvest all; set to specific set if needed
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "daily",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_doab_oaipmh_config():
        """
        Directory of Open Access Books - OAI-PMH ENDPOINT
        ==================================================
        #TAG: OAI-PMH_Harvester #Books #Monographs #Aggregator
        #CONTENT: Open Access book metadata (directory entries)
        #SUBJECTS: All academic disciplines
        #LANGUAGE: Multilingual
        #STATUS: VERIFIED WORKING ✓ (Tested Jan 14, 2026)
        #RESOURCE_TYPE: Book/Monograph (book-level only, no chapters)
        #METADATA_FORMAT: oai_dc, xoai
        
        **VERIFIED**: https://directory.doabooks.org/oai/request responds
        correctly to OAI-PMH protocol with valid OAI 2.0 implementation.
        
        DOAB is an AGGREGATOR that harvests from multiple publishers.
        It provides metadata descriptions only - full text links point
        to publisher websites.
        
        DIFFERENCE FROM OAPEN: DOAB contains only book-level records,
        no chapter-level granularity. DOAB aggregates OAPEN + many other publishers.
        """
        return {
            "name": "DOAB (OAI-PMH) - Books Only",
            "description": "Directory of Open Access Books via OAI-PMH",
            "oaipmh_url": "https://directory.doabooks.org/oai/request",  # CORRECTED
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "daily",
            "max_resources_per_harvest": 5000,
        }

    @staticmethod
    def get_mit_oaipmh_config():
        """
        MIT OpenCourseWare - OAI-PMH ENDPOINT
        ======================================
        #TAG: OAI-PMH_Harvester #Courses #Courseware #Lectures #Higher_Education
        #CONTENT: Complete MIT course materials (syllabi, lectures, assignments)
        #SUBJECTS: STEM, Engineering, Humanities, Social Sciences, Business
        #LANGUAGE: English (some translations)
        #STATUS: ⚠️ ENDPOINT NOT RESPONDING (Tested Jan 14, 2026)
        #RESOURCE_TYPE: Course (complete course materials)
        #WARNING: MIT OCW may have discontinued OAI-PMH support
        
        **ISSUE**: https://ocw.mit.edu/oaipmh does not respond to OAI-PMH requests.
        MIT may have deprecated their OAI-PMH endpoint in favor of other access methods.
        
        MIT OCW contains 2,500+ courses worth of materials including:
        - Complete lecture notes and videos
        - Assignments, exams, solutions
        - Reading lists and syllabi
        - Interactive simulations
        
        **RECOMMENDATION**: Disable this preset OR investigate alternative
        MIT OCW data access methods (RSS feeds, web scraping, etc.)
        """
        return {
            "name": "MIT OpenCourseWare (OAI-PMH) - NOT WORKING",
            "description": "MIT OpenCourseWare OER materials (ENDPOINT NOT RESPONDING)",
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
        Open Education Global Repository - OAI-PMH ENDPOINT
        ====================================================
        #TAG: OAI-PMH_Harvester #Mixed_OER_Types #Global_Repository
        #CONTENT: Conference papers, presentations, teaching materials
        #SUBJECTS: Open Education practice and research
        #LANGUAGE: Multilingual
        #STATUS: ⚠️ ENDPOINT NOT RESPONDING (Tested Jan 14, 2026)
        #RESOURCE_TYPE: Mixed (presentations, papers, lesson plans, etc.)
        
        **ISSUE**: https://repository.oeglobal.org/oai/request does not respond.
        The OE Global repository may have changed its OAI-PMH endpoint URL
        or temporarily unavailable.
        
        OE Global repository contains materials related to Open Education:
        - Conference presentations from OE Global conferences
        - Research papers on OER adoption
        - Case studies and best practices
        - Policy documents
        
        **RECOMMENDATION**: Verify current status before enabling.
        Check https://oeglobal.org for updated API information.
        """
        return {
            "name": "OE Global Repository (OAI-PMH) - NOT RESPONDING",
            "description": "Open Education Global OER repository (NEEDS VERIFICATION)",
            "oaipmh_url": "https://repository.oeglobal.org/oai/request",
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 2000,
        }

    @staticmethod
    def get_skills_commons_oaipmh_config():
        """
        Skills Commons - Workforce Training OER Repository
        ===================================================
        #TAG: OAI-PMH_Harvester #Workforce_Training #Career_Technical_Education
        #CONTENT: Job training materials, workforce development resources
        #SUBJECTS: Career/Technical Education, Workforce Development
        #LANGUAGE: English
        #STATUS: ⚠️ ENDPOINT NOT RESPONDING (Tested Jan 14, 2026)
        #RESOURCE_TYPE: Mixed (lessons, modules, assessments, simulations)
        #PLATFORM: Digital Commons (Elsevier/bePress)
        
        **ISSUE**: https://www.skillscommons.org/oai/request does not respond.
        Skills Commons uses Digital Commons platform which should support OAI-PMH,
        but the endpoint may have changed or requires different URL pattern.
        
        Skills Commons focuses on:
        - Career and Technical Education (CTE) materials
        - Workforce development and job training
        - Community college vocational programs
        - Industry-specific training modules
        - Trade and technical skills
        
        **RECOMMENDATION**: Skills Commons is based on Digital Commons platform.
        Try alternative endpoint: https://www.skillscommons.org/do/oai/
        (Digital Commons standard pattern is /do/oai/)
        """
        return {
            "name": "Skills Commons OER OAI-PMH - NOT RESPONDING",
            "description": "Skills Commons OER via OAI-PMH (NEEDS VERIFICATION)",
            # base endpoint from SkillsCommons OAI docs
            "oaipmh_url": "https://www.skillscommons.org/oai/request",
            # Alternative to try: "https://www.skillscommons.org/do/oai/"
            # you can plug a specific setSpec if you want (e.g. 'publication:OER')
            "oaipmh_set_spec": "",
            "request_params": {"metadataPrefix": "oai_dc"},
            "request_headers": {},
            "harvest_schedule": "weekly",
            "max_resources_per_harvest": 10000,
        }



class PresetCSVConfigs:
    """
    CSV/TSV-based harvesters
    =========================
    These presets harvest from CSV or TSV (tab-separated) data exports.
    Simpler than APIs but less real-time - usually bulk exports updated
    periodically by the source repository.
    
    Good for: One-time bulk imports, KBART library holdings, publisher catalogs
    """

    @staticmethod
    def get_oer_commons_csv_config():
        """
        OER Commons - CSV Export
        =========================
        #TAG: CSV_Harvester #Mixed_OER_Types #K12_Higher_Ed
        #CONTENT: Diverse OER materials (lessons, courses, textbooks, media)
        #SUBJECTS: All K-12 and higher education subjects
        #LANGUAGE: Primarily English
        #STATUS: UNVERIFIED - Export URL may require authentication (Jan 2026)
        #RESOURCE_TYPE: Mixed (textbooks, courses, lessons, videos, simulations)
        
        OER Commons is one of the largest OER repositories with 440,000+ resources.
        It includes materials from multiple sources and allows community curation
        through "hubs" - curated collections organized by topic or institution.
        
        **NOTE**: CSV export may require account login or may be available
        only through their API. Verify access before enabling.
        """
        return {
            "name": "OER Commons CSV",
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
        Skills Commons - CSV Export
        ============================
        #TAG: CSV_Harvester #Workforce_Training #Career_Technical_Education
        #CONTENT: Workforce development OER materials
        #SUBJECTS: Career/Technical Education, Trade Skills
        #LANGUAGE: English
        #STATUS: UNVERIFIED - Export endpoint uncertain (Jan 2026)
        #RESOURCE_TYPE: Mixed training materials
        
        **NOTE**: This CSV endpoint is speculative. Skills Commons may not
        offer direct CSV exports. Consider using OAI-PMH (if fixed) or
        web scraping as alternatives.
        """
        return {
            "name": "Skills Commons OER CSV",
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
        KBART Format Import - Publisher Holdings
        ==========================================
        #TAG: TSV_Harvester #KBART #Library_Holdings #Publisher_Catalogs
        #CONTENT: Standardized library holdings/catalog data
        #SUBJECTS: Any (depends on source)
        #LANGUAGE: Any (depends on source)
        #STATUS: Generic import template (Jan 2026)
        #RESOURCE_TYPE: Serials, Monographs (structured bibliographic data)
        #FORMAT: KBART Phase I/II compliant TSV
        
        KBART (Knowledge Bases And Related Tools) is a NISO standard
        for exchanging library holdings information. Common uses:
        
        - Publisher catalog imports (e.g., Springer, Wiley catalogs)
        - Subscription package definitions
        - Open Access publisher collections
        - Institutional repository exports
        
        **USAGE**: Admin provides KBART file URL when creating harvest source.
        This is a generic template for any KBART-compliant import.
        
        KBART includes fields like:
        - publication_title, print_identifier, online_identifier
        - date_first_issue_online, date_last_issue_online
        - coverage_depth, publisher_name
        """
        return {
            "name": "KBART (TSV) Import",
            "description": "KBART-compliant TSV listing of serials/works; "
                          "upload or provide URL to import.",
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
            "OAPEN MARCXML dump (books). Uses the OAPEN public MARCXML dump URL.\n"
            "#TAG: MARCXML_Harvester #Books #Library_Catalog_Format\n"
            "#CONTENT: Complete OAPEN Library catalog in MARC21 format\n"
            "#STATUS: Verified working (Jan 2026)\n"
            "#RESOURCE_TYPE: Book-level records\n"
            "#NOTE: Full MARC21 bibliographic data, richer than Dublin Core"
        ),
        "marcxml_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_books.xml",
        "harvest_schedule": "manual",
        "max_resources_per_harvest": 5000,
    },
    "doab": {
        "name": "DOAB MARCXML dump",
        "description": (
            "DOAB MARCXML export. Update URL if DOAB changes its MARCXML endpoint.\n"
            "#TAG: MARCXML_Harvester #Books #Library_Catalog_Format\n"
            "#CONTENT: Complete DOAB catalog in MARC21 format\n"
            "#STATUS: Verified working (Jan 2026)\n"
            "#RESOURCE_TYPE: Book-level records\n"
            "#NOTE: Full MARC21 bibliographic data for library catalogs"
        ),
        "marcxml_url": "https://directory.doabooks.org/metadata/marcxml",
        "harvest_schedule": "manual",
        "max_resources_per_harvest": 5000,
    },
}


# =============================================================================
# PRESET TESTING & VALIDATION
# =============================================================================
"""
ENDPOINT VALIDATION STATUS (as of Jan 14, 2026):

✅ WORKING (Tested with OAI-PMH Validator):
    - OAPEN OAI-PMH: https://library.oapen.org/oai/request
    - DOAB OAI-PMH: https://directory.doabooks.org/oai/request

⚠️ NOT RESPONDING (Failed validation tests):
    - MIT OCW OAI-PMH: https://ocw.mit.edu/oaipmh
    - OE Global OAI-PMH: https://repository.oeglobal.org/oai/request  
    - Skills Commons OAI-PMH: https://www.skillscommons.org/oai/request

❓ UNVERIFIED (No public documentation found):
    - MERLOT API: https://api.merlot.org/materials
    - OpenStax API: https://openstax.org/api/v2/pages
    - OER Commons CSV: https://www.oercommons.org/export/csv
    - Skills Commons CSV: https://www.skillscommons.org/export/oer.csv

RECOMMENDATIONS:
1. Enable OAPEN and DOAB OAI-PMH presets immediately (verified working)
2. Disable or mark as experimental: MIT, OE Global, Skills Commons OAI-PMH
3. Investigate alternative access methods for non-responding endpoints
4. For Skills Commons: try Digital Commons standard URL pattern /do/oai/
5. For MIT OCW: consider RSS feeds or web scraping alternatives
6. For MERLOT/OpenStax: contact providers for current API documentation
"""

