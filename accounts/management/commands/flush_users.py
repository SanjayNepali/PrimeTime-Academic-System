# accounts/management/commands/flush_users.py
from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Delete all non-superuser users from the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL users including superusers (dangerous!)',
        )
    
    def handle(self, *args, **options):
        if options['all']:
            count = User.objects.all().count()
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted ALL {count} users'))
        else:
            count = User.objects.filter(is_superuser=False).count()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count} non-superuser users'))