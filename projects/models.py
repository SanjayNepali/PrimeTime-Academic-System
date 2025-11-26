# File: Desktop/Prime/projects/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class Project(models.Model):
    """Student project submissions"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    # Core fields
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        limit_choices_to={'role': 'student'}
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    programming_languages = models.CharField(
        max_length=200,
        help_text="Comma-separated list (e.g., Python, Django, JavaScript)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Review process
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_projects',
        limit_choices_to={'role__in': ['admin', 'superadmin']}  # UPDATED
    )
    review_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Supervisor assignment
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_projects',
        limit_choices_to={'role': 'supervisor'}
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Progress percentage (0-100)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Batch year
    batch_year = models.IntegerField()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['student', 'batch_year']  # One project per student per batch
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['batch_year']),
            models.Index(fields=['student', 'batch_year']),
        ]
        verbose_name = "Student Project"
        verbose_name_plural = "Student Projects"
    
    def __str__(self):
        return f"{self.title} - {self.student.display_name}"
    
    def submit_for_review(self):
        """Submit project for admin review"""
        self.status = 'pending'
        self.submitted_at = timezone.now()
        self.save()
    
    def approve(self, admin_user):
        """Approve the project"""
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.review_date = timezone.now()
        self.rejection_reason = ''
        self.save()
    
    def reject(self, admin_user, reason):
        """Reject the project with reason"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.review_date = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def assign_supervisor(self, supervisor):
        """Assign supervisor to project"""
        self.supervisor = supervisor
        self.status = 'in_progress'
        self.save()
    
    @property
    def is_editable(self):
        """Check if project can be edited"""
        return self.status in ['draft', 'rejected']
    
    @property
    def languages_list(self):
        """Get list of programming languages"""
        return [lang.strip() for lang in self.programming_languages.split(',') if lang.strip()]
    
    @property
    def display_info(self):
        """Display project info for admin"""
        return f"{self.title} ({self.student.display_name} - {self.batch_year})"
    """Student project submissions"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    # Core fields
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        limit_choices_to={'role': 'student'}
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    programming_languages = models.CharField(
        max_length=200,
        help_text="Comma-separated list (e.g., Python, Django, JavaScript)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Review process
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_projects',
        limit_choices_to={'role': 'admin'}
    )
    review_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Supervisor assignment
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_projects',
        limit_choices_to={'role': 'supervisor'}
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Batch year
    batch_year = models.IntegerField()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['student', 'batch_year']  # One project per student per batch
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['batch_year']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.student.username}"
    
    def submit_for_review(self):
        """Submit project for admin review"""
        self.status = 'pending'
        self.submitted_at = timezone.now()
        self.save()
    
    def approve(self, admin_user):
        """Approve the project"""
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.review_date = timezone.now()
        self.rejection_reason = ''
        self.save()
    
    def reject(self, admin_user, reason):
        """Reject the project with reason"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.review_date = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    @property
    def is_editable(self):
        """Check if project can be edited"""
        return self.status in ['draft', 'rejected']
    
    @property
    def languages_list(self):
        """Get list of programming languages"""
        return [lang.strip() for lang in self.programming_languages.split(',')]


class ProjectDeliverable(models.Model):
    """Project deliverables/submissions at different stages"""
    
    STAGE_CHOICES = [
        ('proposal', 'Project Proposal'),
        ('mid_defense', 'Mid Defense'),
        ('pre_defense', 'Pre Defense'),
        ('final_defense', 'Final Defense'),
        ('documentation', 'Final Documentation'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='deliverables'
    )
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    
    # File upload
    document = models.FileField(
        upload_to='documents/deliverables/%Y/%m/',
        help_text="Upload Word document or PDF"
    )
    
    # Review by supervisor
    is_approved = models.BooleanField(default=False)
    marks = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    feedback = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['project', 'stage']
        ordering = ['stage', '-submitted_at']
    
    def __str__(self):
        return f"{self.project.title} - {self.get_stage_display()}"
    
    def approve_with_marks(self, marks, feedback=''):
        """Approve deliverable with marks"""
        self.is_approved = True
        self.marks = marks
        self.feedback = feedback
        self.reviewed_at = timezone.now()
        self.save()
        
        # Update project progress
        self.update_project_progress()
    
    def update_project_progress(self):
        """Calculate and update project progress"""
        total_stages = 5
        completed_stages = self.project.deliverables.filter(is_approved=True).count()
        progress = int((completed_stages / total_stages) * 100)
        
        self.project.progress_percentage = progress
        if progress == 100:
            self.project.status = 'completed'
        else:
            self.project.status = 'in_progress'
        self.project.save()


class ProjectActivity(models.Model):
    """Track all project-related activities"""
    
    ACTION_CHOICES = [
        ('created', 'Project Created'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Project Approved'),
        ('rejected', 'Project Rejected'),
        ('deliverable_submitted', 'Deliverable Submitted'),
        ('deliverable_approved', 'Deliverable Approved'),
        ('supervisor_assigned', 'Supervisor Assigned'),
        ('completed', 'Project Completed'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Project activities'
    
    def __str__(self):
        return f"{self.project.title} - {self.get_action_display()}"