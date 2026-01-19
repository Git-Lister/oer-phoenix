#!/usr/bin/env python
"""Verify OAPEN resources in database."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oer_rebirth.settings')
django.setup()

from resources.models import OERResource, OERSource

print("\n=== Verifying OAPEN Resources in Database ===\n")

# Get test OAPEN sources
sources = OERSource.objects.filter(name__contains="Test OAPEN")
print(f"Found {sources.count()} test OAPEN sources")

for source in sources:
    resources = OERResource.objects.filter(source=source).order_by('-created_at')
    print(f"\nSource: {source.name}")
    print(f"  Total resources: {resources.count()}")
    
    if resources.exists():
        print(f"\n  Sample resources:")
        for r in resources[:3]:
            print(f"\n    Title:      {r.title}")
            print(f"    URL:        {r.url}")
            print(f"    Type:       {r.normalised_type}")
            print(f"    Author:     {r.author[:50] if r.author else '(none)'}")
            print(f"    Publisher:  {r.publisher[:50] if r.publisher else '(none)'}")

print("\n[✓] Database verification complete")
