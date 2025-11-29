# File: Desktop/Prime/resources/management/commands/populate_categories.py
from django.core.management.base import BaseCommand
from resources.models import ResourceCategory

class Command(BaseCommand):
    help = 'Populate project development resource categories for PrimeTime'

    def handle(self, *args, **options):
        # PROJECT DEVELOPMENT LIFECYCLE CATEGORIES
        categories = [
            # ===== 1. PROJECT PLANNING & IDEATION =====
            {
                'name': 'Project Ideation & Planning',
                'icon': 'bx bx-brain',
                'color': '#5568FE',
                'description': 'Brainstorming ideas, project planning, and requirement gathering',
                'order': 1
            },
            {
                'name': 'Proposal Writing', 
                'icon': 'bx bx-edit-alt',
                'color': '#06ffa5',
                'description': 'Writing effective project proposals and research plans',
                'order': 2
            },
            
            # ===== 2. TECHNICAL SKILLS DEVELOPMENT =====
            {
                'name': 'Programming Fundamentals',
                'icon': 'bx bx-code-alt',
                'color': '#ffb700',
                'description': 'Core programming concepts and languages for project development',
                'order': 3
            },
            {
                'name': 'Web Development',
                'icon': 'bx bx-globe',
                'color': '#e91e63',
                'description': 'Frontend, backend, and full-stack web development',
                'order': 4
            },
            {
                'name': 'Mobile Development',
                'icon': 'bx bx-mobile-alt',
                'color': '#9c27b0',
                'description': 'iOS, Android, and cross-platform mobile app development',
                'order': 5
            },
            
            # ===== 3. PROJECT IMPLEMENTATION =====
            {
                'name': 'Database & Backend',
                'icon': 'bx bx-data',
                'color': '#2196f3',
                'description': 'Database design, APIs, server-side development',
                'order': 6
            },
            {
                'name': 'UI/UX Design',
                'icon': 'bx bx-palette',
                'color': '#4caf50',
                'description': 'User interface design, user experience, and prototyping',
                'order': 7
            },
            
            # ===== 4. PROJECT MANAGEMENT & DELIVERY =====
            {
                'name': 'Project Management',
                'icon': 'bx bx-clipboard',
                'color': '#ff9800',
                'description': 'Project planning, task management, and agile methodologies',
                'order': 8
            },
            {
                'name': 'Testing & Deployment',
                'icon': 'bx bx-check-shield',
                'color': '#795548',
                'description': 'Software testing, debugging, and deployment strategies',
                'order': 9
            },
            
            # ===== 5. ACADEMIC & PROFESSIONAL =====
            {
                'name': 'Documentation & Reporting',
                'icon': 'bx bx-book',
                'color': '#607d8b',
                'description': 'Project documentation, technical writing, and reports',
                'order': 10
            },
            {
                'name': 'Presentation & Defense',
                'icon': 'bx bx-presentation',
                'color': '#f44336',
                'description': 'Creating presentations and preparing for project defenses',
                'order': 11
            }
        ]

        created_count = 0
        for cat_data in categories:
            obj, created = ResourceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {cat_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ Already exists: {cat_data["name"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Created {created_count} project development categories!')
        )