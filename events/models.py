# File: events/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import User
from groups.models import Group


class Event(models.Model):
    """Academic events like defense dates, deadlines, meetings"""

    EVENT_TYPES = [
        ('proposal', 'Proposal Defense'),
        ('mid_defense', 'Mid Defense'),
        ('pre_defense', 'Pre Defense'),
        ('final_defense', 'Final Defense'),
        ('deadline', 'Submission Deadline'),
        ('meeting', 'Supervisor Meeting'),
        ('presentation', 'Presentation'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('other', 'Other'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)

    # Timing
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    all_day = models.BooleanField(default=False)

    # Location
    location = models.CharField(max_length=200, blank=True)
    virtual_link = models.URLField(blank=True, help_text="Link for virtual meetings")

    # Associations
    batch_year = models.IntegerField(null=True, blank=True, help_text="If event is for specific batch")
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events',
        help_text="If event is for specific group"
    )
    organizer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organized_events'
    )

    # Attendees
    participants = models.ManyToManyField(
        User,
        related_name='events',
        blank=True,
        help_text="Users invited to this event"
    )

    # Settings
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    is_mandatory = models.BooleanField(default=False)
    send_reminders = models.BooleanField(default=True)
    reminder_hours_before = models.IntegerField(default=24, help_text="Hours before event to send reminder")

    # Submission requirements (for deadline events)
    requires_submission = models.BooleanField(
        default=False,
        help_text="Does this event require file submission?"
    )
    submission_file_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Expected file type (e.g., PDF, DOCX, PPTX)"
    )
    submission_instructions = models.TextField(
        blank=True,
        help_text="Instructions for students on what to submit"
    )
    max_file_size_mb = models.IntegerField(
        default=10,
        help_text="Maximum file size in MB"
    )
    late_submission_penalty = models.FloatField(
        default=10.0,
        help_text="Percentage penalty for late submissions"
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events'
    )

    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'event_type']),
            models.Index(fields=['batch_year', 'is_active']),
            models.Index(fields=['group', 'start_datetime']),
        ]

    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d')}"

    def clean(self):
        """Validate event data"""
        if self.end_datetime and self.start_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError("End datetime must be after start datetime")

    @property
    def duration(self):
        """Get event duration in minutes"""
        if self.end_datetime and self.start_datetime:
            delta = self.end_datetime - self.start_datetime
            return delta.total_seconds() / 60
        return 0

    @property
    def is_upcoming(self):
        """Check if event is in the future"""
        return self.start_datetime > timezone.now()

    @property
    def is_past(self):
        """Check if event has ended"""
        return self.end_datetime < timezone.now()

    @property
    def is_ongoing(self):
        """Check if event is currently happening"""
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime

    @property
    def status_display(self):
        """Get human-readable status"""
        if self.is_cancelled:
            return 'Cancelled'
        elif self.is_ongoing:
            return 'Ongoing'
        elif self.is_past:
            return 'Completed'
        else:
            return 'Upcoming'

    def cancel(self, reason=''):
        """Cancel the event"""
        self.is_cancelled = True
        self.cancellation_reason = reason
        self.save()


class EventReminder(models.Model):
    """Track reminders sent for events"""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_reminders'
    )

    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-reminder_sent_at']

    def __str__(self):
        return f"Reminder for {self.user.username} - {self.event.title}"


class EventAttendance(models.Model):
    """Track attendance for events"""

    ATTENDANCE_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('attended', 'Attended'),
        ('absent', 'Absent'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_attendances'
    )

    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='pending')
    notes = models.TextField(blank=True)

    # RSVP
    rsvp_at = models.DateTimeField(null=True, blank=True)

    # Actual attendance
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-event__start_datetime']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title} ({self.status})"

    def confirm_attendance(self):
        """User confirms they will attend"""
        self.status = 'confirmed'
        self.rsvp_at = timezone.now()
        self.save()

    def decline_attendance(self):
        """User declines to attend"""
        self.status = 'declined'
        self.rsvp_at = timezone.now()
        self.save()

    def check_in(self):
        """Mark user as attended"""
        self.status = 'attended'
        self.checked_in_at = timezone.now()
        self.save()


class Notification(models.Model):
    """System notifications for users"""

    NOTIFICATION_TYPES = [
        ('event_reminder', 'Event Reminder'),
        ('event_update', 'Event Update'),
        ('event_cancelled', 'Event Cancelled'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('project_update', 'Project Update'),
        ('message', 'New Message'),
        ('forum_reply', 'Forum Reply'),
        ('system', 'System Notification'),
        ('other', 'Other'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Content
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()

    # Links
    link_url = models.CharField(max_length=500, blank=True, help_text="URL to redirect when clicked")
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Auto-delete after this date")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}: {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    @classmethod
    def create_for_event(cls, event, users, notification_type='event_reminder', title=None, message=None):
        """Create notifications for multiple users about an event"""
        notifications = []
        for user in users:
            notif = cls.objects.create(
                recipient=user,
                notification_type=notification_type,
                title=title or f"Event: {event.title}",
                message=message or f"You have an event scheduled for {event.start_datetime.strftime('%B %d, %Y at %I:%M %p')}",
                event=event,
                link_url=f"/events/{event.pk}/"
            )
            notifications.append(notif)
        return notifications


class Calendar(models.Model):
    """Academic calendar for batches"""

    name = models.CharField(max_length=100)
    batch_year = models.IntegerField()

    # Academic year dates
    start_date = models.DateField()
    end_date = models.DateField()

    # Important dates
    proposal_deadline = models.DateField(null=True, blank=True)
    mid_defense_start = models.DateField(null=True, blank=True)
    mid_defense_end = models.DateField(null=True, blank=True)
    pre_defense_start = models.DateField(null=True, blank=True)
    pre_defense_end = models.DateField(null=True, blank=True)
    final_defense_start = models.DateField(null=True, blank=True)
    final_defense_end = models.DateField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_calendars'
    )

    class Meta:
        ordering = ['-batch_year']
        unique_together = ['name', 'batch_year']

    def __str__(self):
        return f"{self.name} - Batch {self.batch_year}"

    def clean(self):
        """Validate calendar dates"""
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")

    @property
    def is_current(self):
        """Check if calendar is currently active"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


class EventSubmission(models.Model):
    """Student submissions for deadline events with approval workflow"""

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('supervisor_review', 'Under Supervisor Review'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('supervisor_rejected', 'Supervisor Rejected'),
        ('admin_review', 'Under Admin Review'),
        ('admin_approved', 'Admin Approved - Final'),
        ('admin_rejected', 'Admin Rejected - Final'),
        ('resubmitted', 'Resubmitted'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='submissions',
        limit_choices_to={'event_type': 'deadline'}
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_submissions',
        limit_choices_to={'role': 'student'}
    )

    # Submission details
    submission_file = models.FileField(
        upload_to='event_submissions/%Y/%m/',
        help_text="Uploaded file (PDF, DOCX, PPT, etc.)"
    )
    file_type = models.CharField(max_length=50, blank=True)
    submission_notes = models.TextField(blank=True, help_text="Student's notes about submission")

    # Status tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # Supervisor review
    supervisor_reviewed_at = models.DateTimeField(null=True, blank=True)
    supervisor_remarks = models.TextField(blank=True)
    supervisor_rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        help_text="1-5 rating"
    )

    # Admin review
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True)
    admin_rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        help_text="1-5 rating"
    )

    # Grade impact
    grade_impact = models.FloatField(
        default=0.0,
        help_text="How this submission affects overall grade"
    )
    late_submission = models.BooleanField(default=False)
    late_penalty = models.FloatField(default=0.0, help_text="Penalty for late submission")

    # Versioning (for resubmissions)
    version = models.IntegerField(default=1)
    parent_submission = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resubmissions'
    )

    class Meta:
        ordering = ['-submission_date']
        indexes = [
            models.Index(fields=['event', 'student']),
            models.Index(fields=['status', 'submission_date']),
        ]
        unique_together = ['event', 'student', 'version']

    def __str__(self):
        return f"{self.student.display_name} - {self.event.title} (v{self.version})"

    def is_late(self):
        """Check if submission is late"""
        return self.submission_date > self.event.end_datetime

    def supervisor_approve(self, remarks='', rating=None):
        """Supervisor approves the submission"""
        self.status = 'supervisor_approved'
        self.supervisor_reviewed_at = timezone.now()
        self.supervisor_remarks = remarks
        if rating:
            self.supervisor_rating = rating
        self.save()

        # Send to admin review
        self.status = 'admin_review'
        self.save()

    def supervisor_reject(self, remarks):
        """Supervisor rejects the submission"""
        self.status = 'supervisor_rejected'
        self.supervisor_reviewed_at = timezone.now()
        self.supervisor_remarks = remarks
        self.save()

    def admin_approve(self, remarks='', rating=None):
        """Admin gives final approval"""
        self.status = 'admin_approved'
        self.admin_reviewed_at = timezone.now()
        self.admin_remarks = remarks
        if rating:
            self.admin_rating = rating
        self.save()

    def admin_reject(self, remarks):
        """Admin rejects the submission"""
        self.status = 'admin_rejected'
        self.admin_reviewed_at = timezone.now()
        self.admin_remarks = remarks
        self.save()

    def resubmit(self, new_file, notes=''):
        """Create a resubmission"""
        new_submission = EventSubmission.objects.create(
            event=self.event,
            student=self.student,
            submission_file=new_file,
            submission_notes=notes,
            version=self.version + 1,
            parent_submission=self,
            status='resubmitted'
        )
        return new_submission

    @property
    def final_rating(self):
        """Get final rating (admin if available, otherwise supervisor)"""
        return self.admin_rating or self.supervisor_rating

    @property
    def is_approved(self):
        """Check if submission is finally approved"""
        return self.status == 'admin_approved'

    @property
    def needs_supervisor_review(self):
        """Check if needs supervisor review"""
        return self.status in ['pending', 'resubmitted']

    @property
    def needs_admin_review(self):
        """Check if needs admin review"""
        return self.status in ['supervisor_approved', 'admin_review']