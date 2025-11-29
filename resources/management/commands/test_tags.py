# File: Desktop/Prime/resources/management/commands/test_tags.py
from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceTag
from django.db.models import Count

class Command(BaseCommand):
    help = 'Test the current tags system'

    def handle(self, *args, **options):
        self.stdout.write("🧪 TESTING TAGS SYSTEM...")
        
        # Test 1: Check if any tags exist
        total_tags = ResourceTag.objects.count()
        self.stdout.write(f"\n1️⃣ Total tags in database: {total_tags}")
        
        # Test 2: Check popular tags query
        popular_tags = ResourceTag.objects.annotate(
            resource_count=Count('resource')
        ).order_by('-resource_count')[:15]
        
        self.stdout.write(f"\n2️⃣ Popular tags query returns: {len(popular_tags)} tags")
        
        # Test 3: Show each tag with its count
        self.stdout.write("\n3️⃣ Tag details:")
        for tag in popular_tags:
            self.stdout.write(f"   📍 {tag.name}: {tag.resource_count} resources")
        
        # Test 4: Check if any resources have tags
        resources_with_tags = Resource.objects.filter(tags__isnull=False).count()
        total_resources = Resource.objects.count()
        self.stdout.write(f"\n4️⃣ Resources with tags: {resources_with_tags}/{total_resources}")
        
        # Test 5: Show sample resources and their tags
        self.stdout.write("\n5️⃣ Sample resources and their tags:")
        sample_resources = Resource.objects.prefetch_related('tags')[:5]
        for resource in sample_resources:
            tag_names = [tag.name for tag in resource.tags.all()]
            self.stdout.write(f"   📚 '{resource.title}': {tag_names}")
        
        # Test 6: Check template data availability
        self.stdout.write(f"\n6️⃣ Template would see:")
        self.stdout.write(f"   - popular_tags: {len(popular_tags)} tags")
        if popular_tags:
            self.stdout.write(f"   - First tag: '{popular_tags[0].name}' (count: {popular_tags[0].resource_count})")
        
        self.stdout.write("\n✅ TEST COMPLETE")
