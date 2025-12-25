# File: accounts/models.py - COMPLETE FINAL VERSION

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
import random
import string
from datetime import datetime, time as datetime_time, timedelta
import pytz


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
    
    # ============================================
    # SUPERVISOR SCHEDULE SETTINGS
    # ============================================
    schedule_start_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="Time when students can start messaging (e.g., 09:00 AM)"
    )
    schedule_end_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="Time when students must stop messaging (e.g., 05:00 PM)"
    )
    schedule_days = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated days: Mon,Tue,Wed,Thu,Fri,Sat,Sun"
    )
    schedule_enabled = models.BooleanField(
        default=False,
        help_text="Enable/disable time restrictions for this supervisor"
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
    
    # ============================================
    # FINAL FIXED: SCHEDULE CHECK METHODS
    # All timezone and case sensitivity issues resolved
    # ============================================
    
    def _get_nepal_time(self):
        """Get current time in Nepal timezone explicitly"""
        nepal_tz = pytz.timezone('Asia/Kathmandu')
        utc_now = timezone.now()
        nepal_now = utc_now.astimezone(nepal_tz)
        return nepal_now
    
    def _normalize_day_name(self, day_str):
        """
        Normalize day names to standard 3-letter format
        Handles: Mon, MON, mon, Monday, MONDAY, monday -> Mon
        """
        day_map = {
            'monday': 'Mon',
            'mon': 'Mon',
            'tuesday': 'Tue',
            'tue': 'Tue',
            'wednesday': 'Wed',
            'wed': 'Wed',
            'thursday': 'Thu',
            'thu': 'Thu',
            'friday': 'Fri',
            'fri': 'Fri',
            'saturday': 'Sat',
            'sat': 'Sat',
            'sunday': 'Sun',
            'sun': 'Sun',
        }
        
        day_lower = day_str.strip().lower()
        return day_map.get(day_lower, day_str.strip())
    
    def is_available_now(self):
        """
        FINAL FIXED: Check if supervisor is available for messaging right now
        - Uses Nepal timezone explicitly
        - Handles case-insensitive day names
        - Proper debug logging
        Returns True if available, False if not
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # If schedule not enabled, always available
        if not self.schedule_enabled:
            logger.debug(f"Schedule not enabled for {self.display_name}")
            return True
        
        # If no times set, always available
        if not self.schedule_start_time or not self.schedule_end_time:
            logger.debug(f"No start/end time set for {self.display_name}")
            return True
        
        # Get current time in Nepal timezone
        nepal_now = self._get_nepal_time()
        current_time = nepal_now.time()
        current_day = nepal_now.strftime('%a')  # Mon, Tue, Wed, etc.
        
        logger.debug(f"Checking availability for {self.display_name}")
        logger.debug(f"  Nepal time: {nepal_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.debug(f"  Current time: {current_time}")
        logger.debug(f"  Current day: {current_day}")
        logger.debug(f"  Schedule: {self.schedule_start_time} - {self.schedule_end_time}")
        logger.debug(f"  Schedule days (raw): {self.schedule_days}")
        
        # CRITICAL FIX: Check day with case-insensitive matching
        if self.schedule_days:
            # Normalize all day names in schedule
            raw_days = [d.strip() for d in self.schedule_days.split(',')]
            allowed_days = [self._normalize_day_name(d) for d in raw_days]
            
            logger.debug(f"  Normalized allowed days: {allowed_days}")
            
            if current_day not in allowed_days:
                logger.debug(f"  ❌ Current day '{current_day}' NOT in allowed days {allowed_days}")
                return False
            
            logger.debug(f"  ✅ Current day '{current_day}' IS in allowed days")
        
        # CRITICAL FIX: Proper time comparison
        is_in_time = self.schedule_start_time <= current_time <= self.schedule_end_time
        
        logger.debug(f"  Time check result: {is_in_time}")
        logger.debug(f"  {current_time} between {self.schedule_start_time} and {self.schedule_end_time}")
        
        if is_in_time:
            logger.debug(f"  ✅ AVAILABLE NOW")
        else:
            logger.debug(f"  ❌ NOT AVAILABLE NOW")
        
        return is_in_time
    
    def get_availability_message(self):
        """Get human-readable availability message"""
        if not self.schedule_enabled:
            return "Available anytime"
        
        if not self.schedule_start_time or not self.schedule_end_time:
            return "Available anytime"
        
        # Format times in 12-hour format
        start = self.schedule_start_time.strftime('%I:%M %p')
        end = self.schedule_end_time.strftime('%I:%M %p')
        
        msg = f"Available {start} - {end}"
        
        if self.schedule_days:
            # Normalize day names for display
            raw_days = [d.strip() for d in self.schedule_days.split(',')]
            normalized_days = [self._normalize_day_name(d) for d in raw_days]
            msg += f" on {', '.join(normalized_days)}"
        
        return msg
    
    def get_next_available_time(self):
        """
        FINAL FIXED: Calculate next available time for supervisor
        - Uses Nepal timezone explicitly
        - Handles case-insensitive day names
        """
        if not self.schedule_enabled or not self.schedule_start_time:
            return None
        
        # Get current time in Nepal
        nepal_now = self._get_nepal_time()
        
        # Parse schedule days with normalization
        allowed_days_map = {
            'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3,
            'Fri': 4, 'Sat': 5, 'Sun': 6
        }
        
        allowed_weekdays = []
        if self.schedule_days:
            raw_days = [d.strip() for d in self.schedule_days.split(',')]
            for day in raw_days:
                normalized_day = self._normalize_day_name(day)
                if normalized_day in allowed_days_map:
                    allowed_weekdays.append(allowed_days_map[normalized_day])
        
        # Try next 7 days
        nepal_tz = pytz.timezone('Asia/Kathmandu')
        
        for days_ahead in range(7):
            check_date = nepal_now.date() + timedelta(days=days_ahead)
            check_weekday = check_date.weekday()
            
            # Skip if day not allowed
            if allowed_weekdays and check_weekday not in allowed_weekdays:
                continue
            
            # Combine date with start time in Nepal timezone
            naive_datetime = datetime.combine(check_date, self.schedule_start_time)
            check_datetime = nepal_tz.localize(naive_datetime)
            
            # If this time is in the future, return it
            if check_datetime > nepal_now:
                return check_datetime
        
        return None
    
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
        
        # CRITICAL FIX: Normalize schedule_days on save
        if self.schedule_days:
            raw_days = [d.strip() for d in self.schedule_days.split(',')]
            normalized_days = [self._normalize_day_name(d) for d in raw_days]
            self.schedule_days = ','.join(normalized_days)
        
        super().save(*args, **kwargs)


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
    
    def get_role_display(self):
        """Get human-readable role name"""
        role_dict = dict(User.ROLE_CHOICES)
        return role_dict.get(self.role, self.role)
    
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