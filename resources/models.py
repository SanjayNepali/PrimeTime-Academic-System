# File: Desktop/Prime/resources/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class ResourceCategory(models.Model):
    """Categories for organizing resources"""
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='bx-book')
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#5568FE')  # Hex color for UI
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Resource categories'
    
    def __str__(self):
        return self.name
    
    @property
    def resource_count(self):
        return self.resource_set.count()


class ResourceTag(models.Model):
    """Tags for categorizing resources"""
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Resource(models.Model):
    """Educational resources shared by users"""
    
    RESOURCE_TYPES = [
        ('article', 'Article'),
        ('video', 'Video Tutorial'),
        ('document', 'PDF Document'),
        ('code', 'Code Example'),
        ('link', 'Web Link'),
        ('book', 'Book'),
        ('tool', 'Tool/Software'),
        ('course', 'Online Course'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    category = models.ForeignKey(ResourceCategory, on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_LEVELS, default='beginner')
    
    # Content
    url = models.URLField(blank=True, verbose_name="Resource URL")
    file = models.FileField(upload_to='resources/%Y/%m/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='resources/thumbnails/', blank=True, null=True)
    
    # Tags and Classification
    tags = models.ManyToManyField(ResourceTag, blank=True)
    programming_languages = models.CharField(max_length=200, blank=True)
    estimated_duration = models.IntegerField(
        help_text="Estimated time in minutes", 
        blank=True, 
        null=True,
        validators=[MinValueValidator(1)]
    )
    
    # Metadata
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_resources')
    is_approved = models.BooleanField(default=True)  # For moderation
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement Metrics
    views = models.IntegerField(default=0)
    likes = models.ManyToManyField(User, blank=True, related_name='liked_resources')
    downloads = models.IntegerField(default=0)
    
    # Recommendation system
    relevance_score = models.FloatField(default=0.0)
    average_rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rating_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-is_featured', '-relevance_score', '-created_at']
        indexes = [
            models.Index(fields=['resource_type']),
            models.Index(fields=['category']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['relevance_score']),
        ]
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def increment_downloads(self):
        self.downloads += 1
        self.save(update_fields=['downloads'])
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def is_external_link(self):
        return bool(self.url) and not self.file
    
    @property
    def display_duration(self):
        if self.estimated_duration:
            if self.estimated_duration < 60:
                return f"{self.estimated_duration} min"
            else:
                hours = self.estimated_duration // 60
                minutes = self.estimated_duration % 60
                return f"{hours}h {minutes}min"
        return ""


class ResourceRating(models.Model):
    """User ratings for resources"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'resource']
        ordering = ['-created_at']


class ResourceRecommendation(models.Model):
    """ML-based resource recommendations for students"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_recommendations')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    score = models.FloatField()  # Recommendation confidence score (0-1)
    reason = models.CharField(max_length=200)  # Why recommended
    algorithm_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'resource']
        ordering = ['-score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'score']),
        ]
    
    def mark_clicked(self):
        self.clicked = True
        self.clicked_at = timezone.now()
        self.save()


class ResourceViewHistory(models.Model):
    """Track user resource viewing history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_views')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.IntegerField(default=0)  # in seconds
    completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
        ]