# ============================================
# File: analytics/management/commands/calculate_all_stress.py
# PURPOSE: Fixed manual stress calculation command
# ============================================

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from analytics.sentiment import AdvancedSentimentAnalyzer
from analytics.models import StressLevel


class Command(BaseCommand):
    help = 'Calculate stress levels for all active students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )
        parser.add_argument(
            '--min-stress',
            type=int,
            default=0,
            help='Only show students with stress above this level'
        )

    def handle(self, *args, **options):
        days = options['days']
        min_stress = options['min_stress']
        
        self.stdout.write(self.style.SUCCESS(f'\n🧠 Calculating stress for all students (last {days} days)...\n'))
        
        students = User.objects.filter(role='student', is_active=True)
        
        self.stdout.write(f'Found {students.count()} active students\n')
        
        calculated = 0
        skipped = 0
        high_stress = []
        
        for student in students:
            analyzer = AdvancedSentimentAnalyzer(student)
            result = analyzer.comprehensive_stress_analysis(days=days)
            
            if result:
                calculated += 1
                
                if result.level >= min_stress:
                    # Determine status emoji and color
                    if result.level >= 70:
                        status = self.style.ERROR('🔴 HIGH')
                        high_stress.append((student, result))
                    elif result.level >= 40:
                        status = self.style.WARNING('🟡 MEDIUM')
                    else:
                        status = self.style.SUCCESS('🟢 LOW')
                    
                    self.stdout.write(
                        f'{status} {student.display_name}: {result.level:.1f}%'
                    )
                    
                    # Show breakdown for high stress students
                    if result.level >= 70:
                        self.stdout.write(f'  └─ Chat Sentiment: {result.chat_sentiment_score:.1f}')
                        self.stdout.write(f'  └─ Deadline Pressure: {result.deadline_pressure:.1f}')
                        self.stdout.write(f'  └─ Workload: {result.workload_score:.1f}')
                        self.stdout.write(f'  └─ Social Isolation: {result.social_isolation_score:.1f}\n')
            else:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'⚪ {student.display_name}: Insufficient data')
                )
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Complete: {calculated} calculated, {skipped} skipped'))
        
        if high_stress:
            self.stdout.write(self.style.ERROR(f'\n🚨 HIGH STRESS ALERTS: {len(high_stress)} students'))
            for student, result in high_stress:
                self.stdout.write(
                    self.style.ERROR(f'  • {student.display_name}: {result.level:.1f}%')
                )
