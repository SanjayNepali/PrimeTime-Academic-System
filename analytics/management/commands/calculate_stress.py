# File: analytics/management/commands/calculate_stress.py
# Create these directories first: analytics/management/commands/

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from analytics.sentiment import AdvancedSentimentAnalyzer
from analytics.models import StressLevel


class Command(BaseCommand):
    help = 'Calculate stress levels for all students or a specific student'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            help='Calculate stress for specific user ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Calculate stress for all students',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even if recent analysis exists',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        all_students = options.get('all')
        days = options.get('days')
        force = options.get('force')

        if user_id:
            # Calculate for specific user
            try:
                user = User.objects.get(user_id=user_id, role='student')
                self.calculate_for_user(user, days, force)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Student with ID {user_id} not found'))
        
        elif all_students:
            # Calculate for all students
            students = User.objects.filter(role='student', is_active=True)
            self.stdout.write(f'Found {students.count()} active students')
            
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for student in students:
                result = self.calculate_for_user(student, days, force)
                if result == 'success':
                    success_count += 1
                elif result == 'skipped':
                    skip_count += 1
                else:
                    error_count += 1
            
            self.stdout.write(self.style.SUCCESS(
                f'\nCompleted: {success_count} calculated, {skip_count} skipped, {error_count} errors'
            ))
        
        else:
            self.stdout.write(self.style.ERROR(
                'Please specify --user-id or --all'
            ))

    def calculate_for_user(self, user, days, force):
        """Calculate stress for a single user"""
        try:
            # Check if recent analysis exists
            latest = StressLevel.objects.filter(student=user).order_by('-timestamp').first()
            
            if not force and latest:
                age_hours = (timezone.now() - latest.timestamp).total_seconds() / 3600
                if age_hours < 24:
                    self.stdout.write(
                        f'⏭️  {user.display_name}: Recent analysis exists ({age_hours:.1f}h old)'
                    )
                    return 'skipped'
            
            # Run analysis
            analyzer = AdvancedSentimentAnalyzer(user)
            stress_record = analyzer.comprehensive_stress_analysis(days=days)
            
            if stress_record:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ {user.display_name}: Stress = {stress_record.level:.1f}% '
                    f'({stress_record.stress_category})'
                ))
                
                # Show breakdown
                self.stdout.write(f'  ├─ Chat Sentiment: {stress_record.chat_sentiment_score:.1f}')
                self.stdout.write(f'  ├─ Deadline Pressure: {stress_record.deadline_pressure:.1f}')
                self.stdout.write(f'  ├─ Workload: {stress_record.workload_score:.1f}')
                self.stdout.write(f'  └─ Social Isolation: {stress_record.social_isolation_score:.1f}')
                
                return 'success'
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  {user.display_name}: No meaningful data for analysis'
                ))
                return 'skipped'
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'✗ {user.display_name}: Error - {type(e).__name__}: {str(e)}'
            ))
            return 'error'