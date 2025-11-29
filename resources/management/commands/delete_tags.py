# File: Desktop/Prime/resources/management/commands/delete_tags.py
from django.core.management.base import BaseCommand
from resources.models import ResourceTag

class Command(BaseCommand):
    help = 'Delete all tags while keeping categories intact'

    def handle(self, *args, **options):
        self.stdout.write("🗑️ DELETING TAGS...")
        
        # Count before deletion
        tag_count = ResourceTag.objects.count()
        self.stdout.write(f"Tags to delete: {tag_count}")
        
        if tag_count > 0:
            # Show what we're deleting
            tags = ResourceTag.objects.all()
            for tag in tags:
                self.stdout.write(f"   ❌ {tag.name} ({tag.resource_set.count()} resources)")
            
            # Confirm deletion
            confirm = input(f"\n⚠️  Delete {tag_count} tags? (yes/no): ")
            if confirm.lower() == 'yes':
                # Delete all tags
                deleted_count, _ = ResourceTag.objects.all().delete()
                self.stdout.write(f"✅ Deleted {deleted_count} tags")
            else:
                self.stdout.write("❌ Deletion cancelled")
        else:
            self.stdout.write("✅ No tags to delete")
        
        # Verify categories are intact
        from resources.models import ResourceCategory
        category_count = ResourceCategory.objects.count()
        self.stdout.write(f"\n📂 Categories remaining: {category_count}")