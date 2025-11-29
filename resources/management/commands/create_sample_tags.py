# File: Desktop/Prime/resources/management/commands/create_sample_tags.py
from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceTag
from django.db.models import Count

class Command(BaseCommand):
    help = 'Create sample tags and assign them to resources'

    def handle(self, *args, **options):
        self.stdout.write("🏷️ CREATING SAMPLE TAGS...")
        
        # Step 1: Create common tags for academic projects
        sample_tags = [
            'Python', 'Django', 'JavaScript', 'React', 'HTML/CSS',
            'Database', 'API', 'Web Development', 'Mobile', 'UI/UX',
            'Data Science', 'Machine Learning', 'DevOps', 'Testing',
            'Documentation', 'Presentation', 'Research', 'Tutorial'
        ]
        
        created_count = 0
        for tag_name in sample_tags:
            tag, created = ResourceTag.objects.get_or_create(name=tag_name)
            if created:
                created_count += 1
                self.stdout.write(f"✅ Created: {tag_name}")
        
        self.stdout.write(f"\n📝 Created {created_count} new tags")
        
        # Step 2: Assign tags to existing resources
        resources = Resource.objects.all()
        tags = ResourceTag.objects.all()
        
        self.stdout.write(f"\n🔗 Assigning tags to {resources.count()} resources...")
        
        # Common tag assignments for different resource types
        tag_assignments = {
            'Django': ['Python', 'Django', 'Web Development', 'Backend'],
            'React': ['JavaScript', 'React', 'Frontend', 'Web Development'],
            'Python': ['Python', 'Programming', 'Tutorial'],
            'Web Development': ['HTML/CSS', 'JavaScript', 'Web Development'],
            'Mobile': ['Mobile', 'React', 'JavaScript'],  # For React Native
            'Data Science': ['Python', 'Data Science', 'Machine Learning']
        }
        
        assigned_count = 0
        for resource in resources:
            # Guess tags based on resource title/content
            resource_tags = []
            
            title_lower = resource.title.lower()
            if 'django' in title_lower:
                resource_tags.extend(tag_assignments['Django'])
            elif 'react' in title_lower:
                resource_tags.extend(tag_assignments['React']) 
            elif 'python' in title_lower:
                resource_tags.extend(tag_assignments['Python'])
            elif 'web' in title_lower:
                resource_tags.extend(tag_assignments['Web Development'])
            elif 'mobile' in title_lower:
                resource_tags.extend(tag_assignments['Mobile'])
            elif 'data' in title_lower:
                resource_tags.extend(tag_assignments['Data Science'])
            else:
                # Default tags
                resource_tags.extend(['Tutorial', 'Documentation'])
            
            # Remove duplicates and assign tags
            resource_tags = list(set(resource_tags))
            
            for tag_name in resource_tags:
                try:
                    tag = ResourceTag.objects.get(name=tag_name)
                    resource.tags.add(tag)
                    assigned_count += 1
                except ResourceTag.DoesNotExist:
                    pass
            
            self.stdout.write(f"   📚 '{resource.title}' -> {resource_tags}")
        
        self.stdout.write(f"\n🎯 Assigned {assigned_count} tag relationships")
        
        # Step 3: Show final tag counts
        self.stdout.write("\n📊 FINAL TAG POPULARITY:")
        popular_tags = ResourceTag.objects.annotate(
            resource_count=Count('resource')
        ).order_by('-resource_count')
        
        for tag in popular_tags:
            self.stdout.write(f"   {tag.name}: {tag.resource_count} resources")
        
        self.stdout.write("\n✅ TAGS SYSTEM READY! Popular tags should now work.")