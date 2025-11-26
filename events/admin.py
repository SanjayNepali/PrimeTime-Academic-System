# File: events/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Event, EventReminder, EventAttendance, Notification, Calendar, EventSubmission


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'event_type', 'start_datetime', 'status_badge',
        'organizer_name', 'batch_year', 'participant_count', 'priority_badge'
    ]
    list_filter = ['event_type', 'priority', 'is_active', 'is_cancelled', 'batch_year', 'start_datetime']
    search_fields = ['title', 'description', 'organizer__username', 'location']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = ['participants']
    date_hierarchy = 'start_datetime'

    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'event_type', 'priority')
        }),
        ('Date & Time', {
            'fields': ('start_datetime', 'end_datetime', 'all_day')
        }),
        ('Location', {
            'fields': ('location', 'virtual_link')
        }),
        ('Associations', {
            'fields': ('batch_year', 'group', 'organizer', 'participants')
        }),
        ('Settings', {
            'fields': ('is_mandatory', 'send_reminders', 'reminder_hours_before')
        }),
        ('Status', {
            'fields': ('is_active', 'is_cancelled', 'cancellation_reason')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def organizer_name(self, obj):
        return obj.organizer.get_full_name() if obj.organizer else '—'
    organizer_name.short_description = 'Organizer'

    def participant_count(self, obj):
        count = obj.participants.count()
        return format_html('<span class="badge">{}</span>', count)
    participant_count.short_description = 'Participants'

    def status_badge(self, obj):
        now = timezone.now()
        if obj.is_cancelled:
            color = '#dc3545'
            text = 'Cancelled'
        elif obj.start_datetime > now:
            color = '#28a745'
            text = 'Upcoming'
        elif obj.end_datetime < now:
            color = '#6c757d'
            text = 'Past'
        else:
            color = '#007bff'
            text = 'Ongoing'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        colors = {
            'low': '#6c757d',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    actions = ['cancel_events', 'activate_events']

    def cancel_events(self, request, queryset):
        updated = queryset.update(is_cancelled=True)
        self.message_user(request, f"{updated} event(s) cancelled")
    cancel_events.short_description = "Cancel selected events"

    def activate_events(self, request, queryset):
        updated = queryset.update(is_active=True, is_cancelled=False)
        self.message_user(request, f"{updated} event(s) activated")
    activate_events.short_description = "Activate selected events"


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'is_sent', 'reminder_sent_at']
    list_filter = ['is_sent', 'reminder_sent_at']
    search_fields = ['event__title', 'user__username']
    readonly_fields = ['event', 'user', 'reminder_sent_at']

    def has_add_permission(self, request):
        return False


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = ['event', 'user_name', 'status_badge', 'rsvp_at', 'checked_in_at']
    list_filter = ['status', 'rsvp_at', 'checked_in_at']
    search_fields = ['event__title', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['event', 'user', 'rsvp_at', 'checked_in_at', 'checked_out_at']

    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'User'

    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'confirmed': '#007bff',
            'declined': '#dc3545',
            'attended': '#28a745',
            'absent': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient_name', 'notification_type', 'is_read_badge', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('Links', {
            'fields': ('link_url', 'event')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    def recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username
    recipient_name.short_description = 'Recipient'

    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #28a745;">✓ Read</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ Unread</span>')
    is_read_badge.short_description = 'Status'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{updated} notification(s) marked as read")
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{updated} notification(s) marked as unread")
    mark_as_unread.short_description = "Mark as unread"


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ['name', 'batch_year', 'start_date', 'end_date', 'is_active_badge', 'is_current_badge']
    list_filter = ['batch_year', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Calendar Information', {
            'fields': ('name', 'batch_year', 'is_active')
        }),
        ('Academic Year', {
            'fields': ('start_date', 'end_date')
        }),
        ('Important Deadlines', {
            'fields': (
                'proposal_deadline',
                'mid_defense_start', 'mid_defense_end',
                'pre_defense_start', 'pre_defense_end',
                'final_defense_start', 'final_defense_end'
            )
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Active</span>')
        else:
            return format_html('<span style="color: #6c757d;">✗ Inactive</span>')
    is_active_badge.short_description = 'Active'

    def is_current_badge(self, obj):
        if obj.is_current:
            return format_html('<span style="color: #007bff; font-weight: bold;">Current</span>')
        else:
            return format_html('<span style="color: #6c757d;">—</span>')
    is_current_badge.short_description = 'Current'


# ========== EVENT SUBMISSION ==========
@admin.register(EventSubmission)
class EventSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'student_name', 'event_title', 'version', 'status_badge',
        'submission_date', 'is_late_badge', 'supervisor_rating_display',
        'admin_rating_display', 'final_approval_badge'
    ]
    list_filter = ['status', 'submission_date', 'late_submission', 'version']
    search_fields = ['student__username', 'event__title', 'submission_notes']
    readonly_fields = ['submission_date', 'last_updated', 'supervisor_reviewed_at', 'admin_reviewed_at']
    date_hierarchy = 'submission_date'

    fieldsets = (
        ('Submission Information', {
            'fields': ('event', 'student', 'submission_file', 'file_type', 'submission_notes')
        }),
        ('Status', {
            'fields': ('status', 'version', 'parent_submission', 'late_submission', 'late_penalty')
        }),
        ('Supervisor Review', {
            'fields': ('supervisor_reviewed_at', 'supervisor_remarks', 'supervisor_rating')
        }),
        ('Admin Review', {
            'fields': ('admin_reviewed_at', 'admin_remarks', 'admin_rating')
        }),
        ('Grade Impact', {
            'fields': ('grade_impact',)
        }),
        ('Timestamps', {
            'fields': ('submission_date', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

    def student_name(self, obj):
        return obj.student.display_name
    student_name.short_description = 'Student'

    def event_title(self, obj):
        return obj.event.title
    event_title.short_description = 'Event'

    def status_badge(self, obj):
        status_colors = {
            'pending': '#ffc107',
            'supervisor_review': '#0dcaf0',
            'supervisor_approved': '#198754',
            'supervisor_rejected': '#dc3545',
            'admin_review': '#0d6efd',
            'admin_approved': '#28a745',
            'admin_rejected': '#dc3545',
            'resubmitted': '#fd7e14',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def is_late_badge(self, obj):
        if obj.late_submission:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⏰ Late</span>')
        return format_html('<span style="color: #28a745;">✓ On Time</span>')
    is_late_badge.short_description = 'Submission'

    def supervisor_rating_display(self, obj):
        if obj.supervisor_rating:
            stars = '⭐' * obj.supervisor_rating
            return format_html('<span title="{}/5">{}</span>', obj.supervisor_rating, stars)
        return '-'
    supervisor_rating_display.short_description = 'Supervisor'

    def admin_rating_display(self, obj):
        if obj.admin_rating:
            stars = '⭐' * obj.admin_rating
            return format_html('<span title="{}/5">{}</span>', obj.admin_rating, stars)
        return '-'
    admin_rating_display.short_description = 'Admin'

    def final_approval_badge(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: #28a745; font-weight: bold;">✅ Approved</span>')
        elif obj.status in ['supervisor_rejected', 'admin_rejected']:
            return format_html('<span style="color: #dc3545; font-weight: bold;">❌ Rejected</span>')
        return format_html('<span style="color: #ffc107;">⏳ Pending</span>')
    final_approval_badge.short_description = 'Final Status'

    actions = ['approve_by_supervisor', 'reject_by_supervisor', 'approve_by_admin', 'reject_by_admin']

    def approve_by_supervisor(self, request, queryset):
        count = 0
        for submission in queryset.filter(status__in=['pending', 'resubmitted']):
            submission.supervisor_approve(remarks="Approved by admin panel")
            count += 1
        self.message_user(request, f'{count} submission(s) approved by supervisor')
    approve_by_supervisor.short_description = "Approve as Supervisor"

    def reject_by_supervisor(self, request, queryset):
        count = 0
        for submission in queryset.filter(status__in=['pending', 'resubmitted']):
            submission.supervisor_reject(remarks="Rejected - needs revision")
            count += 1
        self.message_user(request, f'{count} submission(s) rejected by supervisor')
    reject_by_supervisor.short_description = "Reject as Supervisor"

    def approve_by_admin(self, request, queryset):
        count = 0
        for submission in queryset.filter(status__in=['supervisor_approved', 'admin_review']):
            submission.admin_approve(remarks="Final approval by admin")
            count += 1
        self.message_user(request, f'{count} submission(s) approved by admin')
    approve_by_admin.short_description = "Final Approval (Admin)"

    def reject_by_admin(self, request, queryset):
        count = 0
        for submission in queryset.filter(status__in=['supervisor_approved', 'admin_review']):
            submission.admin_reject(remarks="Final rejection by admin")
            count += 1
        self.message_user(request, f'{count} submission(s) rejected by admin')
    reject_by_admin.short_description = "Final Rejection (Admin)"
