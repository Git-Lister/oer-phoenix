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
    
    KEY DIFFERENCES FROM APIs:
    - Standardized XML-based protocol
    - Mandatory Dublin Core support
    - Built-in resumption tokens for large harvests
    - Set-based selective harvesting
    - Datestamp-based incremental updates
    
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
        #SUBJECTS: Career/Technical Education, Workforce Development
        #LANGUAGE: English
        #STATUS: ✅ VERIFIED WORKING (Jan 14, 2026)
        #RESOURCE_TYPE: Mixed (lessons, modules, assessments, simulations)
        #PLATFORM: Digital Commons (Elsevier/bePress)
        
        **VERIFIED**: Correct URL is library.skillscommons.org/server/oai/request
        
        Skills Commons focuses on:
        - Career and Technical Education (CTE) materials
        - Workforce development and job training
        - Community college vocational programs
        - Industry-specific training modules
        - Trade and technical skills
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

    @staticmethod
    def get_mit_oaipmh_config():
        """
        MIT OpenCourseWare - OAI-PMH ENDPOINT
        ======================================
        #TAG: OAI-PMH_Harvester #Courses #Courseware #Higher_Education
        #CONTENT: Complete MIT course materials
        #SUBJECTS: STEM, Engineering, Humanities, Social Sciences, Business
        #LANGUAGE: English (some translations)
        #STATUS: ⚠️ ENDPOINT NOT RESPONDING (Tested Jan 14, 2026)
        #WARNING: MIT OCW may have discontinued OAI-PMH support
        
        **RECOMMENDATION**: Disable this preset or investigate alternative
        MIT OCW data access methods.
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
        Open Education Global Repository - OAI-PMH ENDPOINT
        ====================================================
        #TAG: OAI-PMH_Harvester #Mixed_OER_Types #Global_Repository
        #CONTENT: Conference papers, presentations, teaching materials
        #SUBJECTS: Open Education practice and research
        #LANGUAGE: Multilingual
        #STATUS: ⚠️ ENDPOINT NOT RESPONDING (Tested Jan 14, 2026)
        
        **RECOMMENDATION**: Verify current status before enabling.
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
    Simpler than APIs but less real-time - usually bulk exports updated
    periodically by the source repository.
    
    Good for: One-time bulk imports, KBART library holdings, publisher catalogs
    """

    @staticmethod
    def get_oapen_kbart_config():
        """
        OAPEN Library - KBART Books Export
        ====================================
        #TAG: KBART_Harvester #Books #Tab_Separated #WORKING
        #CONTENT: Complete OAPEN book catalog in KBART format
        #STATUS: ✅ VERIFIED WORKING (Jan 14, 2026)
        #RESOURCE_TYPE: Book-level records
        #FORMAT: Tab-separated values (TSV)
        
        ⭐ RECOMMENDED METHOD for harvesting OAPEN ⭐
        
        OAPEN's OAI-PMH endpoint is currently broken (returns no records).
        Use this KBART export instead for reliable OAPEN harvesting.
        
        Provides standardized bibliographic data including:
        - Title, ISBN, Publisher
        - URLs to full text
        - Coverage dates
        - License information
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
        OER Commons - CSV Export
        =========================
        #TAG: CSV_Harvester #Mixed_OER_Types #K12_Higher_Ed
        #CONTENT: Diverse OER materials (lessons, courses, textbooks, media)
        #SUBJECTS: All K-12 and higher education subjects
        #LANGUAGE: Primarily English
        #STATUS: UNVERIFIED - Export URL may require authentication (Jan 2026)
        #RESOURCE_TYPE: Mixed (textbooks, courses, lessons, videos, simulations)
        
        OER Commons is one of the largest OER repositories with 440,000+ resources.
        
        **NOTE**: CSV export may require account login or may be available
        only through their API. Verify access before enabling.
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
        Skills Commons - CSV Export
        ============================
        #TAG: CSV_Harvester #Workforce_Training #Career_Technical_Education
        #CONTENT: Workforce development OER materials
        #SUBJECTS: Career/Technical Education, Trade Skills
        #LANGUAGE: English
        #STATUS: UNVERIFIED - Export endpoint uncertain (Jan 2026)
        #RESOURCE_TYPE: Mixed training materials
        
        **NOTE**: This CSV endpoint is speculative. Skills Commons may not
        offer direct CSV exports. Consider using OAI-PMH instead (which is working).
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
        "merlot": PresetAPIConfigs.get_merlot_api_config(),
        "openstax": PresetAPIConfigs.get_openstax_api_config(),
    },
    "OAIPMH": {
        # REMOVED: "oapen" - OAI-PMH endpoint broken (empty repository)
        # REMOVED: "doab" - OAI-PMH endpoint returns 503 errors
        "skills_commons": PresetOAIPMHConfigs.get_skills_commons_oaipmh_config(),
        "mit": PresetOAIPMHConfigs.get_mit_oaipmh_config(),
        "oe_global": PresetOAIPMHConfigs.get_oe_global_oaipmh_config(),
    },
    "CSV": {
        "oapen_kbart": PresetCSVConfigs.get_oapen_kbart_config(),  # ⭐ RECOMMENDED for OAPEN
        "oer_commons": PresetCSVConfigs.get_oer_commons_csv_config(),
        "skills_commons_csv": PresetCSVConfigs.get_skills_commons_csv_config(),
        "kbart_generic": PresetCSVConfigs.get_kbart_tsv_config(),
    },
    "MARCXML": {
        "oapen": {
            "name": "OAPEN MARCXML (Books)",
            "description": (
                "OAPEN MARCXML dump (books). Full MARC21 bibliographic data.\n"
                "#TAG: MARCXML_Harvester #Books #Library_Catalog_Format\n"
                "#CONTENT: Complete OAPEN Library catalog in MARC21 format\n"
                "#STATUS: ✅ Verified working (Jan 2026)\n"
                "#RESOURCE_TYPE: Book-level records\n"
                "#NOTE: Richer than Dublin Core, includes full cataloging data"
            ),
            "marcxml_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_books.xml",
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 5000,
        },
        "oapen_chapters": {
            "name": "OAPEN MARCXML (Chapters)",
            "description": (
                "OAPEN MARCXML dump (chapters). Chapter-level records in MARC21.\n"
                "#TAG: MARCXML_Harvester #Book_Chapters #Library_Catalog_Format\n"
                "#CONTENT: OAPEN chapter-level records in MARC21 format\n"
                "#STATUS: ✅ Verified working (Jan 2026)\n"
                "#RESOURCE_TYPE: Chapter-level records"
            ),
            "marcxml_url": "https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_chapters.xml",
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 5000,
        },
        "doab": {
            "name": "DOAB MARCXML",
            "description": (
                "DOAB MARCXML export. Full MARC21 bibliographic data.\n"
                "#TAG: MARCXML_Harvester #Books #Library_Catalog_Format\n"
                "#CONTENT: Complete DOAB catalog in MARC21 format\n"
                "#STATUS: ⚠️ Needs verification (Jan 2026)\n"
                "#RESOURCE_TYPE: Book-level records\n"
                "#NOTE: Full MARC21 bibliographic data for library catalogs"
            ),
            "marcxml_url": "https://directory.doabooks.org/metadata/marcxml",
            "harvest_schedule": "manual",
            "max_resources_per_harvest": 5000,
        },
    },
}


# =============================================================================
# PRESET TESTING & VALIDATION
# =============================================================================
"""
ENDPOINT VALIDATION STATUS (Tested: January 14, 2026)
======================================================

✅ VERIFIED WORKING:
    - Skills Commons OAI-PMH: https://library.skillscommons.org/server/oai/request
    - OAPEN KBART: https://memo.oapen.org/file/oapen/OAPENLibrary_KBART_books.tsv
    - OAPEN MARCXML: https://memo.oapen.org/file/oapen/OAPENLibrary_MARCXML_books.xml
    - OAPEN REST API: https://library.oapen.org/rest/search
    - DOAB REST API: https://directory.doabooks.org/rest/search

❌ BROKEN - DO NOT USE:
    - OAPEN OAI-PMH: https://library.oapen.org/oai/request
      → Repository is EMPTY (returns "No matches" for all queries)
      → Even official documented examples return no records
      → Use KBART/MARCXML/REST API alternatives instead

⚠️ SERVER ERRORS:
    - DOAB OAI-PMH: https://directory.doabooks.org/oai/request
      → Returns 503 Service Unavailable
      → May be temporarily down
      → Use REST API or MARCXML alternatives instead

⚠️ NOT RESPONDING (Endpoints don't respond):
    - MIT OCW OAI-PMH: https://ocw.mit.edu/oaipmh
    - OE Global OAI-PMH: https://repository.oeglobal.org/oai/request

❓ UNVERIFIED (No public documentation found):
    - MERLOT API: https://api.merlot.org/materials
    - OpenStax API: https://openstax.org/api/v2/pages
    - OER Commons CSV: https://www.oercommons.org/export/csv
    - Skills Commons CSV: https://www.skillscommons.org/export/oer.csv

RECOMMENDATIONS:
================
1. ✅ USE: OAPEN KBART preset for OAPEN harvesting (most reliable)
2. ✅ USE: Skills Commons OAI-PMH (working correctly)
3. ✅ USE: REST APIs for OAPEN/DOAB (real-time access)
4. ❌ REMOVED: OAPEN and DOAB from OAIPMH registry (broken/unavailable)
5. ⚠️ MARK AS EXPERIMENTAL: MIT, OE Global (not responding)
6. 🔍 INVESTIGATE: MERLOT, OpenStax (need API documentation)

IMPORTANT NOTES:
================
- OAPEN's OAI-PMH is marked "VERIFIED WORKING" in their docs but is actually EMPTY
- DOAB's OAI-PMH returns 503 errors despite documentation claiming it works
- Skills Commons requires specific URL: library.skillscommons.org/server/oai/request
  (NOT www.skillscommons.org/oai/request as documented elsewhere)
"""
