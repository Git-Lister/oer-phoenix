# resources/management/commands/import_kbart.py

from django.core.management.base import BaseCommand, CommandError
import requests
import os

from resources.models import OERSource
from resources.harvesters.kbart_harvester import KBARTHarvester


class Command(BaseCommand):
    help = "Import a KBART (TSV) file and create OERResources for a given source."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path or URL to KBART TSV file")
        parser.add_argument("source_name", help="Name of the OERSource to attach resources to")
        parser.add_argument(
            "--create-if-missing",
            action="store_true",
            help="Create the OERSource if it does not exist"
        )

    def handle(self, *args, **options):
        path = options["path"]
        source_name = options["source_name"]
        create_if_missing = options["create_if_missing"]

        try:
            # Attempt to download file if URL is provided
            if path.startswith(('http://', 'https://')):
                response = requests.get(path)
                if response.status_code != 200:
                    raise CommandError(f"Failed to download KBART file from {path}")
                
                temp_path = os.path.join(os.getcwd(), "kbart_temp.tsv")
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                path = temp_path

            # Proceed with import
            try:
                source = OERSource.objects.get(name=source_name)
            except OERSource.DoesNotExist:
                if create_if_missing:
                    source = OERSource.objects.create(
                        name=source_name,
                        display_name=source_name,
                        source_type="CSV"
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created OERSource '{source_name}'"))
                else:
                    raise CommandError(
                        f"OERSource '{source_name}' not found. "
                        "Use --create-if-missing to create it."
                    )

            harvester = KBARTHarvester()
            self.stdout.write(f"Harvesting KBART from {path} into source '{source.get_display_name()}...")
            job = harvester.harvest_from_path(source, path)

            # Clean up temporary file if downloaded
            if os.path.exists(temp_path):
                os.remove(temp_path)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Harvest complete: created={job.resources_created} "
                    f"updated={job.resources_updated} failed={job.resources_failed}"
                )
            )

        except Exception as e:
            raise CommandError(f"An error occurred during KBART import: {str(e)}")