# File: forum/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinLengthValidator
from accounts.models import User


class ForumCategory(models.Model):
    """Forum categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='bx-conversation')
    color = models.CharField(max_length=7, default='#5568FE')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Forum categories'
    
    def __str__(self):
        return self.name
    
    # Renamed to avoid potential conflicts
    @property
    def total_posts(self):
        return self.forumpost_set.count()


class ForumTag(models.Model):
    """Tags for forum posts"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    # Renamed to avoid conflict with annotation
    @property
    def total_posts(self):
        return self.forumpost_set.count()


class ForumPost(models.Model):
    """Forum discussion posts"""
    
    POST_TYPES = [
        ('question', 'Question'),
        ('discussion', 'Discussion'),
        ('help', 'Help Request'),
        ('announcement', 'Announcement'),
        ('tutorial', 'Tutorial'),
        ('showcase', 'Project Showcase'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('solved', 'Solved'),
        ('closed', 'Closed'),
        ('pinned', 'Pinned'),
    ]
    
    # Content
    title = models.CharField(max_length=200, validators=[MinLengthValidator(10)])
    content = models.TextField(validators=[MinLengthValidator(20)])
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='question')
    category = models.ForeignKey(ForumCategory, on_delete=models.SET_NULL, null=True)
    
    # Author
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='forum_posts'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_solved = models.BooleanField(default=False)
    solved_by = models.ForeignKey(
        'ForumReply',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solved_posts'
    )
    is_pinned = models.BooleanField(default=False)
    
    # Tags
    tags = models.ManyToManyField(ForumTag, blank=True)
    programming_languages = models.CharField(max_length=200, blank=True)
    
    # Engagement
    views = models.IntegerField(default=0)
    upvotes = models.ManyToManyField(User, blank=True, related_name='upvoted_posts')
    followers = models.ManyToManyField(User, blank=True, related_name='followed_posts')
    
    # Moderation
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    flagged_by = models.ManyToManyField(User, blank=True, related_name='flagged_posts')
    is_hidden = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-last_activity']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['author']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.is_pinned:
            self.status = 'pinned'
        super().save(*args, **kwargs)
    
    @property
    def reply_count(self):
        return self.replies.filter(is_hidden=False).count()
    
    @property
    def upvote_count(self):
        return self.upvotes.count()
    
    @property
    def follower_count(self):
        return self.followers.count()
    
    @property
    def languages_list(self):
        """Return programming languages as a list"""
        if self.programming_languages:
            return [lang.strip() for lang in self.programming_languages.split(',') if lang.strip()]
        return []
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def mark_solved(self, reply):
        """Mark post as solved with specific reply"""
        self.is_solved = True
        self.status = 'solved'
        self.solved_by = reply
        self.save()
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class ForumReply(models.Model):
    """Replies to forum posts"""
    
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(validators=[MinLengthValidator(5)])
    
    # Parent reply for threading
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='child_replies')
    
    # Engagement
    upvotes = models.ManyToManyField(User, blank=True, related_name='upvoted_replies')
    is_accepted = models.BooleanField(default=False)
    
    # Moderation
    is_hidden = models.BooleanField(default=False)
    hidden_reason = models.TextField(blank=True)
    hidden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hidden_replies')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Forum replies'
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Reply to: {self.post.title}"
    
    @property
    def upvote_count(self):
        return self.upvotes.count()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update parent post's last activity
        if self.post:
            self.post.update_last_activity()


class ForumNotification(models.Model):
    """Notifications for forum activity"""
    
    NOTIFICATION_TYPES = [
        ('reply', 'New Reply'),
        ('mention', 'Mention'),
        ('upvote', 'Upvote'),
        ('solution', 'Marked as Solution'),
        ('follow', 'New Follower'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, null=True, blank=True)
    reply = models.ForeignKey(ForumReply, on_delete=models.CASCADE, null=True, blank=True)
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='caused_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} notification for {self.user}"