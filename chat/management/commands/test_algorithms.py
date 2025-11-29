# ============================================
# File: analytics/management/commands/test_algorithms.py
# PURPOSE: Test if your algorithms are working
# ============================================

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from chat.models import Message
from analytics.sentiment import AdvancedSentimentAnalyzer, InappropriateContentDetector
from analytics.models import StressLevel

class Command(BaseCommand):
    help = 'Test if sentiment analysis and stress calculation algorithms are working'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🧪 ALGORITHM TESTING SUITE\n'))
        
        # Test 1: Sentiment Analysis
        self.test_sentiment_analysis()
        
        # Test 2: Inappropriate Content Detection
        self.test_content_detection()
        
        # Test 3: Stress Calculation
        self.test_stress_calculation()
        
        # Test 4: Database Integration
        self.test_database_integration()
        
        self.stdout.write(self.style.SUCCESS('\n✅ All tests completed!'))
    
    def test_sentiment_analysis(self):
        """Test if sentiment analysis is working"""
        self.stdout.write('\n📊 Testing Sentiment Analysis...')
        
        test_messages = [
            ('I am so stressed and overwhelmed with this project', 'negative'),
            ('Great progress today! Feeling confident', 'positive'),
            ('Working on the code', 'neutral'),
            ('I hate this impossible deadline', 'negative'),
        ]
        
        analyzer = AdvancedSentimentAnalyzer(User.objects.first())
        
        for text, expected in test_messages:
            result = analyzer._analyze_single_message(text)
            
            polarity = result['polarity']
            keyword_score = result['keyword_score']
            
            self.stdout.write(f'\nText: "{text[:50]}..."')
            self.stdout.write(f'  Polarity: {polarity:.3f}')
            self.stdout.write(f'  Keyword Score: {keyword_score:.3f}')
            self.stdout.write(f'  Expected: {expected}')
            
            if expected == 'negative' and polarity < 0:
                self.stdout.write(self.style.SUCCESS('  ✅ PASS'))
            elif expected == 'positive' and polarity > 0:
                self.stdout.write(self.style.SUCCESS('  ✅ PASS'))
            elif expected == 'neutral' and -0.1 <= polarity <= 0.1:
                self.stdout.write(self.style.SUCCESS('  ✅ PASS'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ UNEXPECTED'))
    
    def test_content_detection(self):
        """Test inappropriate content detection"""
        self.stdout.write('\n🚫 Testing Content Detection...')
        
        detector = InappropriateContentDetector()
        
        test_cases = [
            ('I hate this stupid project', True, 'Should detect hate speech'),
            ('Check this free money link', True, 'Should detect suspicious content'),
            ('Making good progress on my project', False, 'Should be clean'),
        ]
        
        for text, should_flag, description in test_cases:
            result = detector.analyze_content(text, content_type='chat')
            
            self.stdout.write(f'\nText: "{text}"')
            self.stdout.write(f'  {description}')
            self.stdout.write(f'  Inappropriate: {result["is_inappropriate"]}')
            self.stdout.write(f'  Suspicious: {result["is_suspicious"]}')
            
            if should_flag and (result['is_inappropriate'] or result['is_suspicious']):
                self.stdout.write(self.style.SUCCESS('  ✅ PASS - Correctly flagged'))
            elif not should_flag and not result['is_inappropriate'] and not result['is_suspicious']:
                self.stdout.write(self.style.SUCCESS('  ✅ PASS - Correctly allowed'))
            else:
                self.stdout.write(self.style.ERROR('  ❌ FAIL'))
    
    def test_stress_calculation(self):
        """Test comprehensive stress calculation"""
        self.stdout.write('\n💭 Testing Stress Calculation...')
        
        # Get a student with activity
        students = User.objects.filter(role='student', is_active=True)
        
        if not students.exists():
            self.stdout.write(self.style.WARNING('  ⚠️ No students found in database'))
            return
        
        for student in students[:3]:  # Test first 3 students
            self.stdout.write(f'\nAnalyzing student: {student.display_name}')
            
            # Check prerequisites
            has_messages = Message.objects.filter(sender=student).exists()
            
            self.stdout.write(f'  Has messages: {has_messages}')
            
            if not has_messages:
                self.stdout.write(self.style.WARNING('  ⚠️ No messages - skipping'))
                continue
            
            # Run analysis
            analyzer = AdvancedSentimentAnalyzer(student)
            result = analyzer.comprehensive_stress_analysis(days=7)
            
            if result:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Stress calculated: {result.level:.1f}%'))
                self.stdout.write(f'     Chat sentiment: {result.chat_sentiment_score:.1f}')
                self.stdout.write(f'     Deadline pressure: {result.deadline_pressure:.1f}')
                self.stdout.write(f'     Workload: {result.workload_score:.1f}')
                self.stdout.write(f'     Social isolation: {result.social_isolation_score:.1f}')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ Insufficient data for analysis'))
    
    def test_database_integration(self):
        """Test if data is being saved correctly"""
        self.stdout.write('\n💾 Testing Database Integration...')
        
        # Check recent messages
        recent_messages = Message.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).order_by('-timestamp')[:10]
        
        self.stdout.write(f'\nRecent messages: {recent_messages.count()}')
        
        if recent_messages.exists():
            for msg in recent_messages[:5]:
                self.stdout.write(f'\n  Message ID: {msg.id}')
                self.stdout.write(f'    Sender: {msg.sender.display_name}')
                self.stdout.write(f'    Sentiment: {msg.sentiment_score:.3f}')
                self.stdout.write(f'    Flagged: {msg.is_flagged}')
        
        # Check stress records
        stress_records = StressLevel.objects.all().order_by('-calculated_at')[:5]
        
        self.stdout.write(f'\n\nStress records in database: {StressLevel.objects.count()}')
        
        if stress_records.exists():
            self.stdout.write(self.style.SUCCESS('  ✅ Stress records found'))
            for record in stress_records:
                self.stdout.write(f'\n  Student: {record.student.display_name}')
                self.stdout.write(f'    Level: {record.level:.1f}%')
                self.stdout.write(f'    Calculated: {record.calculated_at}')
        else:
            self.stdout.write(self.style.WARNING('  ⚠️ No stress records - algorithm may not be running'))