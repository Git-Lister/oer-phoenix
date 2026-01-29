from django.urls import path
from . import views
from . import api


app_name = 'resources'


urlpatterns = [
    # Make dashboard the home page
    path('', views.dashboard_view, name='dashboard'),

    # Old home page (to be deprecated)
    path('home/', views.home, name='home'),

    # NEW: Talis A/B analysis flow driven from dashboard
    path('talis/analyse/', views.talis_list_analyse_view, name='talis_analyse_dashboard'),
    path('talis/preview/dashboard/', views.talis_list_preview_view, name='talis_preview_dashboard'),
    path('talis/report/dashboard/', views.talis_list_report_view, name='talis_report_dashboard'),

    # Search and comparison - use resources templates
    path('search/', views.ai_search, name='ai_search'),
    path('compare/', views.compare_view, name='compare_resources'),
    path("advanced-search/", views.advanced_search, name="advanced_search"),

    # Resource detail pages
    path('resource/<int:pk>/', views.resource_detail, name='resource_detail'),
    path('r/<int:pk>/', views.resource_shortlink, name='resource_shortlink'),

    # CSV operations - mixed templates
    path('download-csv/', views.csv_download, name='csv_download'),
    path('upload-csv/', views.csv_upload, name='csv_upload'),  # Admin template
    path('bulk-csv-upload/', views.bulk_csv_upload, name='bulk_csv_upload'),  # Admin template
    path('upload-kbart/', views.kbart_upload, name='kbart_upload'),  # Admin KBART upload

    # Export operations - mixed templates
    path('export/', views.export_resources, name='export_resources'),  # Resources template
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/json/', views.export_json, name='export_json'),
    path('export/talis/', views.export_to_talis, name='export_to_talis'),
    path('export/talis/template/', views.talis_push, name='talis_csv_template'),
    path('export/talis/preview/', views.talis_preview, name='talis_preview'),
    path('export/success/', views.export_success, name='export_success'),
    path('export-data/', views.export_data, name='export_data'),  # Admin template

    # OER Source management (admin functions) - Admin templates
    path('harvest/<int:source_id>/', views.harvest_view, name='harvest_oer_source'),
    path('test-connection/<int:source_id>/', views.test_connection_view, name='test_oer_source_connection'),

    # NEW: Staff maintenance - generate embeddings
    path('embeddings/generate/', views.generate_missing_embeddings, name='generate_embeddings'),

    # API endpoints
    path('api/search/', api.SearchAPIView.as_view(), name='api_search'),
    path('api/rag-answer/', api.rag_answer_view, name='api_rag_answer'),

    # Simple frontend consumer for the API
    path('search/consumer/', views.search_consumer, name='search_consumer'),

    # RAG (Retrieval-Augmented Generation) test interface
    path('rag-test/', views.rag_test_view, name='rag_test'),

    # Existing Talis CSV processing (batch AI search)
    path('talis/upload/', views.bulk_csv_upload, name='talis_csv_upload'),
    path('talis/process/', views.process_talis_csv, name='talis_process_csv'),
    path('talis/report/download/', views.talis_report_download, name='talis_report_download'),
    path('talis/push/', views.talis_push, name='talis_push'),
    path('search/export/talis/', views.search_export_talis, name='search_export_talis'),

    # Admin/demo: list recent Talis push jobs
    path('talis/jobs/', views.talis_jobs, name='talis_jobs'),
]
