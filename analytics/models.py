# File: Desktop/Prime/analytics/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from projects.models import Project


class StressLevel(models.Model):
    """Track student stress levels over time"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stress_levels')
    
    # Overall stress level (0-100)
    level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Component scores
    chat_sentiment_score = models.FloatField(default=0)
    deadline_pressure = models.FloatField(default=0)
    workload_score = models.FloatField(default=0)
    social_isolation_score = models.FloatField(default=0)
    
    # Sentiment analysis results
    positive_messages = models.IntegerField(default=0)
    negative_messages = models.IntegerField(default=0)
    neutral_messages = models.IntegerField(default=0)
    
    # Context
    project_phase = models.CharField(max_length=50, blank=True)
    week_of_semester = models.IntegerField(null=True, blank=True)
    
    # FIXED: Use calculated_at consistently
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['student', 'calculated_at']),
            models.Index(fields=['level']),
        ]
    
    def __str__(self):
        return f"Stress: {self.student.display_name} - {self.level} at {self.calculated_at}"
    
    @property
    def stress_category(self):
        """Get stress category label"""
        if self.level >= 80:
            return "Critical"
        elif self.level >= 60:
            return "High"
        elif self.level >= 40:
            return "Moderate"
        else:
            return "Low"
    
    @property
    def stress_label(self):
        """Get human-readable stress label"""
        if self.level >= 70:
            return "High Stress"
        elif self.level >= 40:
            return "Medium Stress"
        else:
            return "Low Stress"
    
    @property
    def is_high_stress(self):
        """Check if stress level is high"""
        return self.level >= 70
    
    # ========== ADDED: timestamp property for backward compatibility ==========
    @property
    def timestamp(self):
        """Alias for calculated_at for backward compatibility"""
        return self.calculated_at
    
    @timestamp.setter
    def timestamp(self, value):
        """Set calculated_at when timestamp is set"""
        self.calculated_at = value
    # ========== END ADDED PROPERTY ==========


class ProgressTracking(models.Model):
    """Track project progress over time"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_history')
    percentage = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Components of progress
    deliverables_completed = models.IntegerField(default=0)
    total_deliverables = models.IntegerField(default=5)  # Standard stages
    meetings_attended = models.IntegerField(default=0)
    milestones_reached = models.IntegerField(default=0)
    code_commits = models.IntegerField(default=0)
    documentation_pages = models.IntegerField(default=0)
    
    # Quality metrics
    supervisor_satisfaction = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    code_quality_score = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['project', 'timestamp']),
        ]
        unique_together = ['project', 'timestamp']  # One entry per project per timestamp
    
    def __str__(self):
        return f"{self.project.title} - {self.percentage}% at {self.timestamp}"
    
    @property
    def completion_rate(self):
        """Calculate completion rate for deliverables"""
        if self.total_deliverables > 0:
            return (self.deliverables_completed / self.total_deliverables) * 100
        return 0


class SupervisorMeetingLog(models.Model):
    """Log meetings between students and supervisors"""
    
    MEETING_TYPES = [
        ('initial', 'Initial Meeting'),
        ('progress', 'Progress Review'),
        ('technical', 'Technical Discussion'),
        ('feedback', 'Feedback Session'),
        ('final', 'Final Review'),
        ('emergency', 'Emergency Meeting'),
    ]
    
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_meetings',
        limit_choices_to={'role': 'student'}
    )
    supervisor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='supervisor_meetings',
        limit_choices_to={'role': 'supervisor'}
    )
    # FIXED: Changed related_name to avoid clash with projects.SupervisorMeeting
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meeting_logs')
    
    meeting_date = models.DateTimeField()
    duration_minutes = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Meeting details
    meeting_type = models.CharField(max_length=50, choices=MEETING_TYPES)
    location = models.CharField(max_length=100, blank=True, default='Virtual')
    
    topics_discussed = models.TextField()
    action_items = models.TextField(blank=True)
    decisions_made = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Ratings and feedback
    student_preparation_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    meeting_effectiveness_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Validation
    is_verified = models.BooleanField(default=False)
    verified_by_supervisor = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-meeting_date']
        indexes = [
            models.Index(fields=['student', 'meeting_date']),
            models.Index(fields=['supervisor', 'meeting_date']),
            models.Index(fields=['project', 'meeting_date']),
        ]
    
    def __str__(self):
        return f"Meeting: {self.student.display_name} - {self.meeting_date.strftime('%b %d, %Y')}"
    
    def verify_meeting(self, verified_by_supervisor=True):
        """Verify the meeting"""
        self.is_verified = True
        self.verified_by_supervisor = verified_by_supervisor
        self.verified_at = timezone.now()
        self.save()


class SystemAnalytics(models.Model):
    """System-wide analytics data"""
    date = models.DateField(unique=True)
    
    # User metrics
    active_users = models.IntegerField(default=0)
    new_registrations = models.IntegerField(default=0)
    user_retention_rate = models.FloatField(default=0)
    
    # Project metrics
    total_projects = models.IntegerField(default=0)
    projects_created = models.IntegerField(default=0)
    projects_completed = models.IntegerField(default=0)
    average_completion_time = models.FloatField(default=0)  # in days
    
    # Resource metrics
    resource_views = models.IntegerField(default=0)
    resource_downloads = models.IntegerField(default=0)
    forum_posts_created = models.IntegerField(default=0)
    
    # Performance metrics
    average_stress_level = models.FloatField(default=0)
    system_uptime = models.FloatField(default=100.0)  # percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'System analytics'
    
    def __str__(self):
        return f"Analytics for {self.date}"


class SupervisorFeedback(models.Model):
    """Supervisor feedback log sheet for students"""

    RATING_CHOICES = [
        (1, '1 - Needs Significant Improvement'),
        (2, '2 - Below Expectations'),
        (3, '3 - Meets Expectations'),
        (4, '4 - Above Expectations'),
        (5, '5 - Excellent'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_feedback',
        limit_choices_to={'role': 'student'}
    )
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_feedback',
        limit_choices_to={'role': 'supervisor'}
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='supervisor_feedback'
    )

    # Log sheet details
    date = models.DateField(default=timezone.now)
    context = models.CharField(
        max_length=200,
        help_text="Brief context of the feedback session"
    )
    remarks = models.TextField(help_text="Detailed feedback and remarks")

    # Analysis
    sentiment_score = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        help_text="Calculated sentiment of remarks"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        help_text="Overall performance rating"
    )

    # Action tracking
    action_required = models.BooleanField(
        default=False,
        help_text="Does this feedback require immediate action?"
    )
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Does this require a follow-up?"
    )
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="When to follow up"
    )

    # Visibility
    is_visible_to_student = models.BooleanField(
        default=True,
        help_text="Should student see this feedback?"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Supervisor Feedback'
        verbose_name_plural = 'Supervisor Feedback'
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['supervisor', 'date']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"Feedback for {self.student.display_name} on {self.date}"

    def calculate_sentiment(self):
        """Calculate sentiment of the remarks"""
        try:
            from textblob import TextBlob
            blob = TextBlob(self.remarks)
            self.sentiment_score = blob.sentiment.polarity
            self.save(update_fields=['sentiment_score'])
        except Exception as e:
            print(f"Error calculating sentiment: {e}")
            self.sentiment_score = 0.0

    @property
    def sentiment_category(self):
        """Categorize sentiment"""
        if self.sentiment_score is None:
            return "Neutral"
        if self.sentiment_score > 0.3:
            return "Positive"
        elif self.sentiment_score < -0.3:
            return "Negative"
        return "Neutral"

    @property
    def rating_display(self):
        """Get rating as string"""
        if self.rating:
            return dict(self.RATING_CHOICES)[self.rating]
        return "Not Rated"


class SystemActivity(models.Model):
    """Track system-wide activities for admin dashboard"""
    
    ACTIVITY_TYPES = [
        ('stress_analysis', 'Stress Analysis'),
        ('feedback_added', 'Feedback Added'),
        ('meeting_logged', 'Meeting Logged'),
        ('project_created', 'Project Created'),
        ('deliverable_submitted', 'Deliverable Submitted'),
        ('deliverable_approved', 'Deliverable Approved'),
        ('user_created', 'User Created'),
        ('user_login', 'User Login'),
        ('group_created', 'Group Created'),
        ('system_event', 'System Event'),
        ('analytics_run', 'Analytics Run'),
    ]
    
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_activities')
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional context
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'System Activities'
        indexes = [
            models.Index(fields=['activity_type', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def icon_class(self):
        """Get appropriate icon for activity type"""
        icons = {
            'stress_analysis': 'bx bx-heart-circle',
            'feedback_added': 'bx bx-comment-detail',
            'meeting_logged': 'bx bx-calendar-event',
            'project_created': 'bx bx-briefcase',
            'deliverable_submitted': 'bx bx-paper-plane',
            'deliverable_approved': 'bx bx-check-circle',
            'user_created': 'bx bx-user-plus',
            'user_login': 'bx bx-log-in',
            'group_created': 'bx bx-group',
            'system_event': 'bx bx-cog',
            'analytics_run': 'bx bx-bar-chart',
        }
        return icons.get(self.activity_type, 'bx bx-info-circle')
    
    @property
    def badge_class(self):
        """Get appropriate badge color for activity type"""
        badges = {
            'stress_analysis': 'bg-info',
            'feedback_added': 'bg-warning',
            'meeting_logged': 'bg-primary',
            'project_created': 'bg-success',
            'deliverable_submitted': 'bg-secondary',
            'deliverable_approved': 'bg-success',
            'user_created': 'bg-info',
            'user_login': 'bg-secondary',
            'group_created': 'bg-primary',
            'system_event': 'bg-dark',
            'analytics_run': 'bg-info',
        }
        return badges.get(self.activity_type, 'bg-secondary')