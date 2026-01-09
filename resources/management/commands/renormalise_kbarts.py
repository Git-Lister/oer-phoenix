# resources/management/commands/renormalise_kbarts.py
from django.core.management.base import BaseCommand
from django.db.models import Count
from resources.models import OERResource

TYPE_MAP = {
    "book": "book", "monograph": "book", "textbook": "book",
    "chapter": "chapter", "book chapter": "chapter",
    "article": "article", "journal article": "article", "paper": "article",
    "video": "video", "lecture": "video",
    "course": "course", "module": "course",
    "ebook": "book", "journal": "journal",
    "audio": "audio", "image": "image", "other": "other",
}

def infer_from_strings(s):
    if not s:
        return "book"
    val = s.lower().strip()
    for needle, code in TYPE_MAP.items():
        if needle in val:
            return code
    return "book"

class Command(BaseCommand):
    help = "Re-normalise KBART resources (source ID 51)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        kbarts = OERResource.objects.filter(source_id=51)
        total = kbarts.count()
        print(f"Found {total} KBART resources")
        
        # Current counts (no dict() conversion)
        print("normalised_type counts:", 
              dict(kbarts.values('normalised_type').annotate(c=Count('normalised_type'))))
        print("resource_type counts:", 
              dict(kbarts.values('resource_type').annotate(c=Count('resource_type'))))
        
        changed = 0
        for obj in kbarts.iterator(chunk_size=500):
            old = obj.normalised_type or ""
            new = infer_from_strings(obj.resource_type)
            if old != new:
                print(f"CHANGE {obj.id}: '{old}' → '{new}' (raw='{obj.resource_type}')")
                changed += 1
                if not dry_run:
                    obj.normalised_type = new
                    obj.save(update_fields=["normalised_type"])
        
        print(f"Would change {changed}/{total}")
