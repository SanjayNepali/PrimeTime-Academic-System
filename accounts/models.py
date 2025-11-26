# File: Desktop/Prime/accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
import random
import string


class User(AbstractUser):
    """Custom User model with simplified role system"""
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('supervisor', 'Supervisor'),
    ]
    
    # Core fields
    user_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True
    )
    
    # User information
    full_name = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True)
    enrollment_year = models.IntegerField(null=True, blank=True)
    
    # Password management
    initial_password = models.CharField(max_length=20, blank=True)
    initial_password_visible = models.BooleanField(default=True)
    password_changed = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    
    # Account status
    is_enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )
    
    # Batch management
    batch_year = models.IntegerField(
        choices=[(year, str(year)) for year in range(2079, 2090)],
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['role']),
            models.Index(fields=['batch_year']),
            models.Index(fields=['password_changed']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.role or 'No Role'})"
    
    def generate_initial_password(self):
        """Generate a secure initial password with special characters"""
        upper = ''.join(random.choices(string.ascii_uppercase, k=2))
        digits = ''.join(random.choices(string.digits, k=4))
        lower = ''.join(random.choices(string.ascii_lowercase, k=2))
        special = random.choice('!@#$%')
        self.initial_password = f"{upper}{digits}{lower}{special}"
        self.initial_password_visible = True
        return self.initial_password
    
    def mark_password_changed(self):
        """Mark that user has changed their initial password"""
        self.password_changed = True
        self.must_change_password = False
        self.password_changed_at = timezone.now()
        self.initial_password_visible = False
        self.save()
    
    # Simplified role properties
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_supervisor(self):
        return self.role == 'supervisor'
    
    @property
    def display_name(self):
        """Display name that uses full_name first, then falls back"""
        return self.full_name or self.get_full_name() or self.username
    
    def save(self, *args, **kwargs):
        """Ensure user_id is set for students and handle username generation"""
        if self.is_student and not self.user_id:
            self.user_id = f"STU{random.randint(10000, 99999)}"
        
        if not self.username and self.email:
            self.username = self.email.split('@')[0]
        
        super().save(*args, **kwargs)


# Keep UserProfile, LoginHistory, and UniversityDatabase models the same as before
class UserProfile(models.Model):
    """Extended profile for users"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Profile info
    profile_picture = models.ImageField(
        upload_to='profiles/%Y/%m/',
        blank=True,
        null=True
    )
    bio = models.TextField(max_length=500, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # Student-specific fields
    student_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    enrollment_date = models.DateField(null=True, blank=True)
    
    # Supervisor-specific fields
    specialization = models.CharField(max_length=200, blank=True)
    max_groups = models.IntegerField(default=3)
    
    # Settings
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    
    # Activity tracking
    last_seen = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"Profile of {self.user.display_name}"
    
    def update_last_seen(self):
        """Update last seen timestamp and online status"""
        self.last_seen = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_seen', 'is_online'])
    
    def set_offline(self):
        """Mark user as offline"""
        self.is_online = False
        self.save(update_fields=['is_online'])


class LoginHistory(models.Model):
    """Track user login history"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
        verbose_name_plural = 'Login histories'
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.user.username} - {status} - {self.login_time}"


class UniversityDatabase(models.Model):
    """Simulated university database for user lookup"""
    
    user_id = models.CharField(max_length=20, unique=True, primary_key=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    enrollment_year = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    class Meta:
        verbose_name = "University Database Entry"
        verbose_name_plural = "University Database"
    
    def __str__(self):
        return f"{self.user_id} - {self.full_name}"
    
    def create_user_from_entry(self, created_by=None):
        """Create a User instance from this database entry"""
        user = User(
            user_id=self.user_id,
            username=self.email.split('@')[0],
            email=self.email,
            full_name=self.full_name,
            department=self.department,
            role=self.role,
            enrollment_year=self.enrollment_year,
            phone=self.phone,
            created_by=created_by
        )
        
        initial_password = user.generate_initial_password()
        user.set_password(initial_password)
        user.must_change_password = True
        user.initial_password_visible = True
        user.save()
        
        UserProfile.objects.create(user=user)
        
        return user