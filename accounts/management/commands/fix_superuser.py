# File: Desktop/Prime/accounts/management/commands/fix_superuser.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix superuser accounts to work with the system'

    def handle(self, *args, **options):
        # Fix all superusers
        superusers = User.objects.filter(is_superuser=True)
        
        for user in superusers:
            # Ensure superuser settings
            user.must_change_password = False
            user.password_changed = True
            user.is_enabled = True
            
            # Don't set role for superusers - they use is_superuser flag instead
            # This prevents the "invalid role" error
            
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Fixed superuser: {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {superusers.count()} superuser(s)')
        )