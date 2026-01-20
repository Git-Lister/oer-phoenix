"""
Management command to show RAG feedback analytics and query statistics.

Usage:
    python manage.py rag_analytics [--export] [--format csv|json]
"""

from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Display RAG (Retrieval-Augmented Generation) analytics and usage statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export feedback log to file'
        )
        parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            default='json',
            help='Export format (default: json)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                "RAG Analytics Command\n"
                "======================\n\n"
                "Feedback tracking is client-side via localStorage.\n"
                "To view feedback data:\n"
                "1. Open browser DevTools (F12)\n"
                "2. Go to Application → Local Storage\n"
                "3. Look for key: 'rag_feedback_log'\n\n"
                "Example feedback entry:\n"
                '{"query": "What is machine learning?", "feedback": "helpful", "timestamp": "2025-01-20T14:00:00Z"}\n\n'
                "For server-side tracking in a future update:\n"
                "- Add RAGFeedback model to models.py\n"
                "- Create API endpoint POST /api/rag-feedback/\n"
                "- Send feedback from JS to backend\n"
                "- Run 'python manage.py migrate' to create table\n"
            )
        )

        if options.get('export'):
            self.stdout.write(
                self.style.WARNING(
                    "Export functionality requires server-side feedback tracking.\n"
                    "Set up a RAGFeedback model first."
                )
            )
