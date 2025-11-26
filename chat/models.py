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