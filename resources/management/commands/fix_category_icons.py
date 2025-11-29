# File: Desktop/Prime/resources/management/commands/fix_category_icons.py
from django.core.management.base import BaseCommand
from resources.models import ResourceCategory

class Command(BaseCommand):
    help = 'Fix missing category icons'

    def handle(self, *args, **options):
        # Define proper icons for each category
        category_updates = {
            'Project Ideation & Planning': 'bx bx-brain',
            'Proposal Writing': 'bx bx-edit-alt',
            'Programming Fundamentals': 'bx bx-code-alt',
            'Web Development': 'bx bx-globe',
            'Mobile Development': 'bx bx-mobile-alt',
            'Database & Backend': 'bx bx-data',
            'UI/UX Design': 'bx bx-palette',
            'Project Management': 'bx bx-clipboard',
            'Testing & Deployment': 'bx bx-check-shield',
            'Documentation & Reporting': 'bx bx-book',
            'Presentation & Defense': 'bx bx-slideshow',  # This was missing!
        }

        updated_count = 0
        for category_name, icon in category_updates.items():
            try:
                category = ResourceCategory.objects.get(name=category_name)
                if category.icon != icon:
                    category.icon = icon
                    category.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Updated icon for: {category_name} -> {icon}')
                    )
            except ResourceCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Category not found: {category_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Updated icons for {updated_count} categories!')
        )