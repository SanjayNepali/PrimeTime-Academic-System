# File: Desktop/Prime/analytics/sentiment.py

from textblob import TextBlob
import re
import numpy as np
import logging
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from collections import Counter

from chat.models import Message
from analytics.models import StressLevel
from projects.models import Project, ProjectDeliverable

logger = logging.getLogger(__name__)


class AdvancedSentimentAnalyzer:
    """Advanced sentiment analysis with multiple data sources"""
    
    def __init__(self, user):
        self.user = user
        self.project = self._get_user_project()
        
        # Enhanced keyword lists with weights
        self.STRESS_KEYWORDS = {
            'stressed': 2.0, 'anxious': 2.0, 'overwhelmed': 2.5, 'exhausted': 2.0,
            'frustrated': 1.5, 'stuck': 1.5, 'impossible': 2.0, 'failing': 2.5,
            'deadline': 1.0, 'pressure': 1.5, 'difficult': 1.0, 'hard': 1.0,
            'cannot': 1.0, 'help': 0.5, 'confused': 1.0, 'worried': 1.5,
            'nervous': 1.5, 'panic': 2.5, 'burnout': 3.0, 'depressed': 3.0
        }
        
        self.POSITIVE_KEYWORDS = {
            'happy': 1.5, 'excited': 1.5, 'progress': 1.0, 'completed': 1.5,
            'successful': 1.5, 'great': 1.0, 'good': 0.5, 'excellent': 1.5,
            'achieved': 1.0, 'solved': 1.5, 'fixed': 1.0, 'working': 0.5,
            'confident': 1.0, 'proud': 1.5, 'relieved': 1.0, 'optimistic': 1.0
        }
    
    def _get_user_project(self):
        """Get user's current project"""
        try:
            return Project.objects.get(
                student=self.user,
                batch_year=timezone.now().year
            )
        except (Project.DoesNotExist, Project.MultipleObjectsReturned):
            return None
    
    def comprehensive_stress_analysis(self, days=7):
        """Comprehensive stress analysis using multiple data sources"""
        
        stress_data = {
            'chat_sentiment': self._analyze_chat_sentiment(days),
            'project_progress': self._analyze_project_progress(),
            'deadline_pressure': self._calculate_deadline_pressure(),
            'workload_assessment': self._assess_workload(),
            'social_engagement': self._analyze_social_engagement(days)
        }
        
        # Calculate overall stress level
        overall_stress = self._calculate_comprehensive_stress(stress_data)
        
        # Save to database
        return self._save_stress_analysis(stress_data, overall_stress)
    
    def _analyze_chat_sentiment(self, days):
        """Temporary simplified chat sentiment analysis"""
        # Return default values until chat system is properly set up
        return {
            'score': 50,  # Neutral default
            'message_count': 0,
            'avg_sentiment': 0,
            'avg_keyword_score': 0,
            'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0}
        }
    
    def _analyze_single_message(self, text):
        """Analyze a single message with enhanced features"""
        # Clean text
        text_clean = re.sub(r'[^\w\s]', '', text.lower())
        words = text_clean.split()
        
        # TextBlob sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Keyword analysis with weights
        stress_score = sum(self.STRESS_KEYWORDS.get(word, 0) for word in words)
        positive_score = sum(self.POSITIVE_KEYWORDS.get(word, 0) for word in words)
        
        # Net keyword score (positive reduces stress)
        keyword_score = stress_score - positive_score
        
        # Exclamation and question mark analysis
        exclamation_count = text.count('!')
        question_count = text.count('?')
        
        # Adjust for emotional intensity
        if exclamation_count > 2:
            if polarity < 0:
                keyword_score += 1.0  # Negative excitement increases stress
            else:
                keyword_score -= 0.5  # Positive excitement reduces stress
        
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'keyword_score': keyword_score,
            'word_count': len(words),
            'exclamation_count': exclamation_count,
            'question_count': question_count
        }
    
    def _analyze_project_progress(self):
        """Analyze project progress and its impact on stress"""
        if not self.project:
            return {'score': 0, 'progress': 0, 'behind_schedule': False}
        
        progress = self.project.progress_percentage
        
        # Expected progress based on time elapsed
        project_start = self.project.created_at
        project_duration = 180  # Assume 6-month project
        days_elapsed = (timezone.now() - project_start).days
        
        expected_progress = min(100, (days_elapsed / project_duration) * 100)
        
        # Progress stress: being behind schedule increases stress
        progress_gap = expected_progress - progress
        progress_stress = max(0, min(100, progress_gap * 2))  # 2x multiplier for being behind
        
        # Recent activity check
        recent_activity = ProjectDeliverable.objects.filter(
            project=self.project,
            submitted_at__gte=timezone.now() - timedelta(days=7)
        ).exists()
        
        if not recent_activity and progress < 90:
            progress_stress += 10  # Penalty for inactivity
        
        return {
            'score': progress_stress,
            'progress': progress,
            'expected_progress': expected_progress,
            'behind_schedule': progress_gap > 10,
            'recent_activity': recent_activity
        }
    
    def _calculate_deadline_pressure(self):
        """Calculate pressure from upcoming deadlines"""
        if not self.project:
            return {'score': 0, 'upcoming_deadlines': 0}
        
        # Get upcoming deliverables
        upcoming_deliverables = ProjectDeliverable.objects.filter(
            project=self.project,
            is_approved=False
        )
        
        deadline_pressure = 0
        
        for deliverable in upcoming_deliverables:
            # Simple deadline pressure calculation
            days_until_deadline = 14  # Assume 2 weeks for each deliverable
            pressure = max(0, (1 - (days_until_deadline / 14)) * 50)  # Max 50 per deliverable
            deadline_pressure += pressure
        
        # Cap the pressure
        deadline_pressure = min(100, deadline_pressure)
        
        return {
            'score': deadline_pressure,
            'upcoming_deadlines': upcoming_deliverables.count(),
            'deliverable_details': [
                {
                    'stage': deliverable.get_stage_display(),
                    'submitted': bool(deliverable.submitted_at)
                }
                for deliverable in upcoming_deliverables
            ]
        }
    
    def _assess_workload(self):
        """Assess current workload based on project complexity and progress"""
        if not self.project:
            return {'score': 0, 'complexity': 'unknown'}
        
        # Estimate workload based on project factors
        workload_score = 0
        
        # Project size (based on description length)
        description_complexity = min(1.0, len(self.project.description) / 1000)
        workload_score += description_complexity * 30
        
        # Technology stack complexity
        tech_complexity = min(1.0, len(self.project.languages_list) / 5)
        workload_score += tech_complexity * 40
        
        # Progress pressure (being in the middle of project is most stressful)
        progress = self.project.progress_percentage
        if 20 <= progress <= 80:
            workload_score += 30  # Middle phase is most intensive
        
        return {
            'score': min(100, workload_score),
            'complexity': 'high' if workload_score > 60 else 'medium' if workload_score > 30 else 'low',
            'technology_count': len(self.project.languages_list),
            'description_length': len(self.project.description)
        }
    
    def _analyze_social_engagement(self, days):
        """Temporary simplified social engagement"""
        return {
            'score': 50,  # Neutral default
            'sent_messages': 0,
            'received_messages': 0,
            'total_interactions': 0,
            'isolation_level': 'medium'
        }
    
    def _calculate_comprehensive_stress(self, stress_data):
        """Calculate comprehensive stress level using weighted factors"""
        weights = {
            'chat_sentiment': 0.25,
            'project_progress': 0.25,
            'deadline_pressure': 0.20,
            'workload_assessment': 0.20,
            'social_engagement': 0.10
        }
        
        total_stress = 0
        
        for factor, weight in weights.items():
            factor_data = stress_data[factor]
            total_stress += factor_data['score'] * weight
        
        return min(100, total_stress)
    
    def _normalize_chat_stress(self, sentiment, keyword_score):
        """Normalize chat analysis to 0-100 stress scale"""
        # Sentiment: -1 (very negative) to 1 (very positive) -> 100 to 0 stress
        sentiment_stress = (1 - ((sentiment + 1) / 2)) * 100
        
        # Keyword score: higher positive = more stress
        keyword_stress = min(100, max(0, keyword_score * 10 + 50))
        
        # Combine with 60-40 weighting
        return (sentiment_stress * 0.6) + (keyword_stress * 0.4)
    
    def _get_sentiment_breakdown(self, sentiments):
        """Get breakdown of sentiment categories"""
        positive = sum(1 for s in sentiments if s > 0.1)
        negative = sum(1 for s in sentiments if s < -0.1)
        neutral = len(sentiments) - positive - negative
        
        return {
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_ratio': positive / len(sentiments) if sentiments else 0,
            'negative_ratio': negative / len(sentiments) if sentiments else 0
        }
    
    def _save_stress_analysis(self, stress_data, overall_stress):
        """Save comprehensive stress analysis to database"""
        return StressLevel.objects.create(
            student=self.user,
            level=overall_stress,
            chat_sentiment_score=stress_data['chat_sentiment']['score'],
            deadline_pressure=stress_data['deadline_pressure']['score'],
            workload_score=stress_data['workload_assessment']['score'],
            social_isolation_score=stress_data['social_engagement']['score'],
            positive_messages=stress_data['chat_sentiment']['sentiment_breakdown'].get('positive', 0),
            negative_messages=stress_data['chat_sentiment']['sentiment_breakdown'].get('negative', 0),
            neutral_messages=stress_data['chat_sentiment']['sentiment_breakdown'].get('neutral', 0),
            project_phase=self._get_project_phase(),
            week_of_semester=self._get_week_of_semester()
        )
    
    def _get_project_phase(self):
        """Determine current project phase"""
        if not self.project:
            return "unknown"
        
        progress = self.project.progress_percentage
        
        if progress < 20:
            return "initial"
        elif progress < 50:
            return "mid-phase"
        elif progress < 80:
            return "final-phase"
        else:
            return "completion"
    
    def _get_week_of_semester(self):
        """Calculate current week of semester"""
        # Simple implementation - can be enhanced with actual semester dates
        year_start = timezone.datetime(timezone.now().year, 1, 1).date()
        current_date = timezone.now().date()
        week_number = (current_date - year_start).days // 7
        
        return min(52, max(1, week_number))


class InappropriateContentDetector:
    """Enhanced inappropriate content detection"""
    
    def __init__(self):
        self.INAPPROPRIATE_PATTERNS = [
            (r'\b(spam|scam|fake|phishing)\b', 'Spam content'),
            (r'\b(hate|racist|sexist|discriminat)\b', 'Hate speech'),
            (r'\b(violence|threat|harm|kill|attack)\b', 'Violent content'),
            (r'\b(cheat|plagiar|copy|steal)\b', 'Academic dishonesty'),
            (r'\b(profanity|curse|swear)\b', 'Inappropriate language'),
            (r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 'Suspicious links'),
        ]
        
        self.SUSPICIOUS_PATTERNS = [
            (r'\b(password|login|credit.?card|social.?security)\b', 'Sensitive information'),
            (r'\b(free.?money|earn.?fast|get.?rich)\b', 'Suspicious offers'),
        ]
    
    def analyze_content(self, text, content_type='forum'):
        """Comprehensive content analysis"""
        text_lower = text.lower()
        
        # Check for inappropriate content
        inappropriate_issues = []
        for pattern, reason in self.INAPPROPRIATE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                inappropriate_issues.append(reason)
        
        # Check for suspicious content
        suspicious_issues = []
        for pattern, reason in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                suspicious_issues.append(reason)
        
        # Sentiment analysis for extreme negativity
        blob = TextBlob(text)
        if blob.sentiment.polarity < -0.7:
            inappropriate_issues.append("Extremely negative/hostile content")
        
        # Length check for spam
        if len(text.strip()) < 10 and content_type == 'forum':
            inappropriate_issues.append("Very short content - possible spam")
        
        # Multiple exclamation marks
        if text.count('!') > 5:
            suspicious_issues.append("Excessive excitement - possible spam")
        
        return {
            'is_inappropriate': len(inappropriate_issues) > 0,
            'is_suspicious': len(suspicious_issues) > 0,
            'inappropriate_issues': inappropriate_issues,
            'suspicious_issues': suspicious_issues,
            'sentiment_score': blob.sentiment.polarity,
            'severity_level': self._calculate_severity(inappropriate_issues, suspicious_issues)
        }
    
    def _calculate_severity(self, inappropriate_issues, suspicious_issues):
        """Calculate severity level of detected issues"""
        if any(issue in ['Hate speech', 'Violent content'] for issue in inappropriate_issues):
            return 'high'
        elif inappropriate_issues:
            return 'medium'
        elif suspicious_issues:
            return 'low'
        else:
            return 'none'