# resources/management/commands/normalise_resource_types.py
from django.core.management.base import BaseCommand
from django.db.models import Q
from resources.models import OERResource


# Only explicit, positive mappings here
TYPE_MAP = {
    "book": "book",
    "monograph": "book",
    "textbook": "book",
    "chapter": "chapter",
    "book chapter": "chapter",
    "article": "article",
    "journal article": "article",
    "paper": "article",
    "conference paper": "article",

    # Periodicals
    "periodical": "periodical",
    "fulltext": "periodical",
    "journal": "periodical",
    "magazine": "periodical",
    "serial": "periodical",

    # AV & other
    "video": "video",
    "lecture": "video",
    "course": "course",
    "module": "course",
    "ebook": "book",
    "audio": "audio",
    "image": "image",
    "other": "other",
}

# Raw strings that really do mean “other”
EXPLICIT_OTHER = {
    "other",
    "misc",
    "mixed",
    "multi-part",
}

MONOGRAPH_SOURCES = {
    "OAPEN Library - OAIPMH",
    "DOAB - OAIPMH",
}

# Kbart-mapped types that we might see in resource_type
KBART_LABELS = {
    "ebook": "Book",
    "journal": "Journal",
    "audio": "Audio",
    "video": "Video",
    "image": "Image",
    "other": "Other",
}



def infer_from_strings(s: str | None) -> str | None:
    if not s:
        return None
    val = s.lower().strip()

    # If the source said “other”-like explicitly, accept that
    if val in EXPLICIT_OTHER:
        return "other"

    for needle, code in TYPE_MAP.items():
        if needle in val:
            return code

    # explicit “unknown” buckets become None so they stay Unspecified
    if "unknown" in val or "unspecified" in val:
        return None

    # Anything else: no decision
    return None


def infer_from_title(title: str | None) -> str | None:
    if not title:
        return None
    t = title.lower()
    if "chapter " in t or "ch. " in t:
        return "chapter"
    if "lesson " in t or "unit " in t:
        return "course"
    return None


def infer_from_identifiers(obj: OERResource) -> str | None:
    if obj.isbn:
        return "book"
    if obj.doi and not obj.isbn:
        return "article"
    return None


def infer_fallback(obj: OERResource) -> str | None:
    # If source is known monograph-only, treat missing type as book
    src_name = getattr(obj.source, "name", "") or ""
    if src_name in MONOGRAPH_SOURCES:
        return "book"
    return None


class Command(BaseCommand):
    help = "Backfill normalised_type for legacy OERResource rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without writing changes; only log counts.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        qs = OERResource.objects.filter(
            Q(normalised_type__isnull=True) |
            Q(normalised_type__exact="") |
            Q(normalised_type__in=[
                "ebook", "e-book",
                "audio", "fulltext", "periodical",
                "other",
            ])
        )

        totals = 0
        by_type = {
            "book": 0,
            "chapter": 0,
            "article": 0,
            "video": 0,
            "course": 0,
            "other": 0,
            "skipped": 0,
        }

        for obj in qs.iterator(chunk_size=500):
            totals += 1

            current = (obj.normalised_type or "").strip()
            if current:
                by_type[current] = by_type.get(current, 0) + 1
                continue

            t = infer_from_strings(obj.resource_type)
            if not t:
                t = infer_from_title(obj.title)
            if not t:
                t = infer_from_identifiers(obj)
            if not t:
                t = infer_fallback(obj)

            # IMPORTANT CHANGE:
            # Do NOT force “other” just because resource_type is non-empty.
            # If we still have no decision, leave it as skipped.
            if not t:
                by_type["skipped"] += 1
                continue

            by_type[t] = by_type.get(t, 0) + 1

            if not dry_run:
                obj.normalised_type = t
                obj.save(update_fields=["normalised_type"])

        self.stdout.write(self.style.SUCCESS(f"Processed {totals} records"))
        for k, v in sorted(by_type.items()):
            self.stdout.write(f"  {k}: {v}")
