# File: Desktop/Prime/chat/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from groups.models import Group


class ChatRoom(models.Model):
    """Chat room for group communication"""
    
    ROOM_TYPES = [
        ('group', 'Group Chat'),
        ('direct', 'Direct Message'),
        ('supervisor', 'Supervisor Chat'),
    ]
    
    # Room details
    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='group')
    
    # Relationships
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_room'
    )
    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        blank=True
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(
        default=False,
        help_text="Frozen rooms can only be accessed during supervisor-defined hours"
    )
    
    # Chat schedule (for supervisor-controlled rooms)
    schedule_start_time = models.TimeField(null=True, blank=True)
    schedule_end_time = models.TimeField(null=True, blank=True)
    schedule_days = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated days: Mon,Tue,Wed,Thu,Fri,Sat,Sun"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['room_type', 'is_active']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    def is_accessible_now(self):
        """Check if room is accessible at current time"""
        if not self.is_frozen:
            return True
        
        if not self.schedule_start_time or not self.schedule_end_time:
            return True
        
        now = timezone.now()
        current_time = now.time()
        current_day = now.strftime('%a')
        
        # Check if current day is in schedule
        if self.schedule_days:
            allowed_days = [day.strip() for day in self.schedule_days.split(',')]
            if current_day not in allowed_days:
                return False
        
        # Check if current time is in schedule
        return self.schedule_start_time <= current_time <= self.schedule_end_time
    
    @property
    def message_count(self):
        """Get total message count"""
        return self.messages.count()
    
    @property
    def unread_count_for_user(self, user):
        """Get unread message count for a specific user"""
        if not user.is_authenticated:
            return 0
        
        try:
            member = self.members.get(user=user)
            return self.messages.filter(
                timestamp__gt=member.last_read_at
            ).exclude(sender=user).count()
        except ChatRoomMember.DoesNotExist:
            return 0


class ChatRoomMember(models.Model):
    """Track chat room membership and read status"""
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    
    # Read tracking
    last_read_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    notifications_enabled = models.BooleanField(default=True)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['room', 'user']
        ordering = ['-last_seen_at']
    
    def __str__(self):
        return f"{self.user.display_name} in {self.room.name}"
    
    def mark_as_read(self):
        """Mark all messages as read up to now"""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen_at = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_seen_at', 'is_online'])


class Message(models.Model):
    """Chat message"""
    
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('file', 'File Attachment'),
        ('image', 'Image'),
        ('system', 'System Message'),
    ]
    
    # Message details
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    
    # File attachment
    attachment = models.FileField(
        upload_to='chat/attachments/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Reply/thread support
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Sentiment analysis
    sentiment_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Sentiment score from -1 (negative) to 1 (positive)"
    )
    
    # Moderation
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Read tracking
    read_by = models.ManyToManyField(
        User,
        related_name='read_messages',
        blank=True
    )
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['is_flagged']),
        ]
    
    def __str__(self):
        return f"{self.sender.display_name}: {self.content[:50]}"
    
    def mark_as_read_by(self, user):
        """Mark message as read by user"""
        self.read_by.add(user)
    
    def soft_delete(self):
        """Soft delete the message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = "[Message deleted]"
        self.save()
    
    @property
    def read_count(self):
        """Get count of users who have read this message"""
        return self.read_by.count()
    
    @property
    def display_content(self):
        """Get display content (handles deleted messages)"""
        if self.is_deleted:
            return "[Message deleted]"
        return self.content


class MessageReaction(models.Model):
    """Reactions to messages (emoji reactions)"""
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)  # Emoji unicode
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user', 'emoji']
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.display_name} reacted {self.emoji} to message"


class TypingIndicator(models.Model):
    """Track who is currently typing in a room"""
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='typing_indicators')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.display_name} typing in {self.room.name}"
    
    @classmethod
    def cleanup_old_indicators(cls, seconds=10):
        """Remove typing indicators older than specified seconds"""
        cutoff = timezone.now() - timezone.timedelta(seconds=seconds)
        cls.objects.filter(started_at__lt=cutoff).delete()


class ChatNotification(models.Model):
    """Notifications for chat events"""
    
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('mention', 'Mention'),
        ('reply', 'Reply to Message'),
        ('room_created', 'Room Created'),
        ('member_added', 'Member Added'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user.display_name}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()

class PendingMessage(models.Model):
    """
    Messages sent by students when supervisor is unavailable
    These are queued and delivered when supervisor becomes available
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    # Message details
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='pending_messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_pending_messages'
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to='pending_chat_attachments/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Threading support
    reply_to = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_replies'
    )
    
    # Supervisor to deliver to
    target_supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pending_messages_to_receive',
        limit_choices_to={'role': 'supervisor'}
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Sentiment (analyzed when sent)
    sentiment_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    is_flagged = models.BooleanField(default=False)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_delivery_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this message should be delivered"
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_origin'
    )
    
    # Expiry (optional - messages expire after X days)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Message expires if not delivered by this time"
    )
    
    # Metadata
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_delivery_time']),
            models.Index(fields=['target_supervisor', 'status']),
            models.Index(fields=['sender', 'status']),
        ]
    
    def __str__(self):
        return f"Pending from {self.sender.display_name} to {self.target_supervisor.display_name} - {self.status}"
    
    def calculate_delivery_time(self):
        """Calculate when this message should be delivered based on supervisor schedule"""
        if not self.target_supervisor.schedule_enabled:
            # No schedule, deliver immediately
            return timezone.now()
        
        now = timezone.now()
        
        # If supervisor is available right now, deliver immediately
        if self.target_supervisor.is_available_now():
            return now
        
        # Calculate next available time
        return self.get_next_available_time()
    
    def get_next_available_time(self):
        """Get the next time supervisor will be available"""
        supervisor = self.target_supervisor
        now = timezone.now()
        
        # Parse schedule days
        allowed_days = []
        if supervisor.schedule_days:
            day_map = {
                'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3,
                'Fri': 4, 'Sat': 5, 'Sun': 6
            }
            for day in supervisor.schedule_days.split(','):
                day = day.strip()
                if day in day_map:
                    allowed_days.append(day_map[day])
        
        # Try next 7 days
        for days_ahead in range(7):
            check_date = now.date() + timezone.timedelta(days=days_ahead)
            check_weekday = check_date.weekday()
            
            # Check if day is allowed
            if allowed_days and check_weekday not in allowed_days:
                continue
            
            # Combine date with start time
            delivery_time = timezone.datetime.combine(
                check_date,
                supervisor.schedule_start_time
            )
            
            # Make timezone aware
            if timezone.is_naive(delivery_time):
                delivery_time = timezone.make_aware(delivery_time)
            
            # If this time is in the future, use it
            if delivery_time > now:
                return delivery_time
        
        # Fallback: deliver in 24 hours
        return now + timezone.timedelta(hours=24)
    
    def deliver(self):
        """Convert pending message to actual message and mark as delivered"""
        if self.status != 'pending':
            return None
        
        try:
            # Create the actual message
            message = Message.objects.create(
                room=self.room,
                sender=self.sender,
                content=self.content,
                attachment=self.attachment,
                reply_to=self.reply_to,
                sentiment_score=self.sentiment_score,
                is_flagged=self.is_flagged,
                message_type='text'
            )
            
            # Update pending message status
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.delivered_message = message
            self.save()
            
            # Update room's last message time
            self.room.last_message_at = timezone.now()
            self.room.save(update_fields=['last_message_at'])
            
            return message
        
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.attempts += 1
            self.last_attempt_at = timezone.now()
            self.save()
            return None
    
    def mark_expired(self):
        """Mark message as expired"""
        self.status = 'expired'
        self.save()
    
    @property
    def time_until_delivery(self):
        """Get timedelta until delivery"""
        if self.scheduled_delivery_time and self.status == 'pending':
            return self.scheduled_delivery_time - timezone.now()
        return None
    
    @property
    def is_ready_for_delivery(self):
        """Check if message is ready to be delivered"""
        if self.status != 'pending':
            return False
        
        # Check if supervisor is available now
        if not self.target_supervisor.is_available_now():
            return False
        
        # Check if scheduled time has passed
        if self.scheduled_delivery_time and timezone.now() < self.scheduled_delivery_time:
            return False
        
        return True