from django.core.management.base import BaseCommand
from resources.models import OERResource


class Command(BaseCommand):
    help = "Remove noise-word subjects (The, This, In, etc.)"

    def handle(self, *args, **options):
        NOISE_SUBJECTS = {
            'the', 'this', 'these', 'that', 'there', 'in', 'on', 'at', 
            'an', 'a', 'by', 'to', 'for', 'with', 'while', 'few', 'some',
            'introduction', 'overview',
        }
        
        qs = OERResource.objects.exclude(subject='')
        cleaned = 0
        
        for obj in qs.iterator(chunk_size=500):
            if obj.subject.lower() in NOISE_SUBJECTS:
                self.stdout.write(f"Clearing: [{obj.id}] '{obj.subject}'")
                obj.subject = ''
                obj.save(update_fields=['subject'])
                cleaned += 1
        
        self.stdout.write(self.style.SUCCESS(f"Cleaned {cleaned} noise subjects"))
