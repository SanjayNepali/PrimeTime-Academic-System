# File: analytics/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import StressLevel, ProgressTracking, SupervisorMeetingLog, SystemAnalytics, SupervisorFeedback


# ========== STRESS LEVEL ==========
@admin.register(StressLevel)
class StressLevelAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'level_badge', 'category_badge', 'timestamp', 'project_phase']
    list_filter = ['project_phase', 'timestamp']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Student Information', {'fields': ('student', 'timestamp')}),
        ('Stress Metrics', {
            'fields': (
                'level', 'stress_category', 'chat_sentiment_score',
                'deadline_pressure', 'workload_score', 'social_isolation_score'
            )
        }),
        ('Message Analysis', {
            'fields': ('positive_messages', 'negative_messages', 'neutral_messages')
        }),
        ('Context', {'fields': ('project_phase', 'week_of_semester')}),
    )

    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username
    student_name.short_description = 'Student'

    def level_badge(self, obj):
        if obj.level >= 80:
            color = '#dc3545'
        elif obj.level >= 60:
            color = '#fd7e14'
        elif obj.level >= 40:
            color = '#ffc107'
        else:
            color = '#28a745'
        return format_html('<span style="color: {}; font-weight: bold;">{:.1f}%</span>', color, obj.level)
    level_badge.short_description = 'Stress Level'

    def category_badge(self, obj):
        color_map = {
            'Low': '#28a745',
            'Moderate': '#ffc107',
            'High': '#fd7e14',
            'Critical': '#dc3545'
        }
        color = color_map.get(obj.stress_category, '#6c757d')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>',
                           color, obj.stress_category.upper())
    category_badge.short_description = 'Category'


# ========== PROGRESS TRACKING ==========
@admin.register(ProgressTracking)
class ProgressTrackingAdmin(admin.ModelAdmin):
    list_display = ['project', 'percentage', 'completion_rate_display', 'supervisor_satisfaction', 'timestamp']
    list_filter = ['timestamp', 'percentage']
    search_fields = ['project__title', 'project__student__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

    def completion_rate_display(self, obj):
        return f"{obj.completion_rate:.1f}%"
    completion_rate_display.short_description = 'Completion Rate'


# ========== SUPERVISOR MEETING LOG ==========
@admin.register(SupervisorMeetingLog)
class SupervisorMeetingLogAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'supervisor_name', 'meeting_type', 'duration_display',
                   'meeting_effectiveness_rating', 'meeting_date']
    list_filter = ['meeting_type', 'meeting_date', 'meeting_effectiveness_rating']
    search_fields = ['student__username', 'supervisor__username', 'topics_discussed']
    readonly_fields = ['created_at']
    date_hierarchy = 'meeting_date'

    def student_name(self, obj):
        return obj.student.get_full_name()
    student_name.short_description = 'Student'

    def supervisor_name(self, obj):
        return obj.supervisor.get_full_name()
    supervisor_name.short_description = 'Supervisor'

    def duration_display(self, obj):
        return f"{obj.duration_minutes} min"
    duration_display.short_description = 'Duration'


# ========== SYSTEM ANALYTICS ==========
@admin.register(SystemAnalytics)
class SystemAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'active_users', 'total_projects', 'average_stress_level', 'system_uptime']
    list_filter = ['date']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'


# ========== SUPERVISOR FEEDBACK ==========
@admin.register(SupervisorFeedback)
class SupervisorFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'student_name', 'supervisor_name', 'date', 'rating_display_badge',
        'sentiment_badge', 'action_required_badge', 'is_visible_to_student'
    ]
    list_filter = ['date', 'rating', 'action_required', 'is_visible_to_student', 'follow_up_required']
    search_fields = ['student__username', 'supervisor__username', 'context', 'remarks']
    readonly_fields = ['created_at', 'updated_at', 'sentiment_score', 'sentiment_category']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'supervisor', 'project', 'date')
        }),
        ('Feedback Details', {
            'fields': ('context', 'remarks', 'rating')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment_score', 'sentiment_category'),
            'classes': ('collapse',)
        }),
        ('Action Tracking', {
            'fields': ('action_required', 'follow_up_required', 'follow_up_date')
        }),
        ('Visibility', {
            'fields': ('is_visible_to_student',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def student_name(self, obj):
        return obj.student.display_name
    student_name.short_description = 'Student'

    def supervisor_name(self, obj):
        return obj.supervisor.display_name
    supervisor_name.short_description = 'Supervisor'

    def rating_display_badge(self, obj):
        if not obj.rating:
            return format_html('<span style="color: #6c757d;">Not Rated</span>')

        color_map = {
            1: '#dc3545',
            2: '#fd7e14',
            3: '#ffc107',
            4: '#28a745',
            5: '#0d6efd'
        }
        color = color_map.get(obj.rating, '#6c757d')
        stars = '⭐' * obj.rating
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ({})</span>',
            color, stars, obj.rating
        )
    rating_display_badge.short_description = 'Rating'

    def sentiment_badge(self, obj):
        if obj.sentiment_score is None:
            return '-'

        if obj.sentiment_score > 0.3:
            icon = '😊'
            color = '#28a745'
            label = 'Positive'
        elif obj.sentiment_score < -0.3:
            icon = '😞'
            color = '#dc3545'
            label = 'Negative'
        else:
            icon = '😐'
            color = '#ffc107'
            label = 'Neutral'

        return format_html(
            '<span style="color: {};">{} {} ({:.2f})</span>',
            color, icon, label, obj.sentiment_score
        )
    sentiment_badge.short_description = 'Sentiment'

    def action_required_badge(self, obj):
        if obj.action_required:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠️ Yes</span>')
        return format_html('<span style="color: #28a745;">✓ No</span>')
    action_required_badge.short_description = 'Action Required'

    actions = ['calculate_sentiment_for_selected', 'mark_as_visible', 'mark_as_hidden']

    def calculate_sentiment_for_selected(self, request, queryset):
        count = 0
        for feedback in queryset:
            feedback.calculate_sentiment()
            count += 1
        self.message_user(request, f'Calculated sentiment for {count} feedback entries')
    calculate_sentiment_for_selected.short_description = 'Calculate sentiment'

    def mark_as_visible(self, request, queryset):
        updated = queryset.update(is_visible_to_student=True)
        self.message_user(request, f'{updated} feedback entries marked as visible to students')
    mark_as_visible.short_description = 'Make visible to students'

    def mark_as_hidden(self, request, queryset):
        updated = queryset.update(is_visible_to_student=False)
        self.message_user(request, f'{updated} feedback entries hidden from students')
    mark_as_hidden.short_description = 'Hide from students'
