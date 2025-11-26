# File: Desktop/Prime/accounts/management/commands/migrate_roles.py

from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Migrate admin roles to superadmin'

    def handle(self, *args, **options):
        # Update all admin roles to superadmin
        updated = User.objects.filter(role='admin').update(role='superadmin')
        self.stdout.write(f'Updated {updated} users from admin to superadmin')
        
        # Ensure all superusers have superadmin role
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            if not user.role:
                user.role = 'superadmin'
                user.save()
                self.stdout.write(f'Set role for superuser: {user.username}')