# File: forum/management/commands/setup_forum.py

from django.core.management.base import BaseCommand
from forum.models import ForumCategory, ForumTag


class Command(BaseCommand):
    help = 'Setup forum with initial categories and tags'

    def handle(self, *args, **kwargs):
        # Create categories
        categories = [
            {
                'name': 'General Discussion',
                'description': 'General academic and project discussions',
                'icon': 'bx-conversation',
                'color': '#5568FE',
                'order': 1
            },
            {
                'name': 'Technical Help',
                'description': 'Get help with technical issues and programming',
                'icon': 'bx-code-alt',
                'color': '#10B981',
                'order': 2
            },
            {
                'name': 'Project Ideas',
                'description': 'Share and discuss project ideas',
                'icon': 'bx-bulb',
                'color': '#F59E0B',
                'order': 3
            },
            {
                'name': 'Announcements',
                'description': 'Important announcements and updates',
                'icon': 'bx-bell',
                'color': '#EF4444',
                'order': 4
            },
            {
                'name': 'Tutorials',
                'description': 'Share tutorials and learning resources',
                'icon': 'bx-book-open',
                'color': '#8B5CF6',
                'order': 5
            },
        ]

        for cat_data in categories:
            category, created = ForumCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(f'Category already exists: {category.name}')

        # Create tags
        tags = [
            'Python', 'Django', 'JavaScript', 'React', 'Node.js',
            'Database', 'API', 'Frontend', 'Backend', 'Debugging',
            'Machine Learning', 'Data Science', 'Web Development',
            'Mobile Development', 'DevOps', 'Testing', 'Security',
            'Performance', 'Design', 'UI/UX', 'Git', 'Docker'
        ]

        for tag_name in tags:
            tag, created = ForumTag.objects.get_or_create(name=tag_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created tag: {tag.name}'))
            else:
                self.stdout.write(f'Tag already exists: {tag.name}')

        self.stdout.write(self.style.SUCCESS('\nForum setup completed successfully!'))