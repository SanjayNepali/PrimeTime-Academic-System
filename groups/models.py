# File: groups/models.py - COMPLETE FIXED VERSION

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from accounts.models import User


class Group(models.Model):
    """Project groups supervised by faculty"""
    
    name = models.CharField(max_length=100)
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='supervised_groups',
        limit_choices_to={'role': 'supervisor'}
    )
    
    # Group constraints
    min_students = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)]
    )
    max_students = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1)]
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    batch_year = models.IntegerField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups'
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['name', 'batch_year']
        indexes = [
            models.Index(fields=['supervisor', 'is_active']),
            models.Index(fields=['batch_year']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.batch_year}) - {self.supervisor.display_name}"
    
    @property
    def student_count(self):
        """Get current number of active students"""
        return self.members.filter(is_active=True).count()
    
    @property
    def is_full(self):
        """Check if group has reached maximum capacity"""
        return self.student_count >= self.max_students
    
    @property
    def available_slots(self):
        """Get number of available slots"""
        return max(0, self.max_students - self.student_count)
    
    @property
    def can_start(self):
        """Check if group meets minimum requirements"""
        return self.student_count >= self.min_students
    
    def add_student(self, student, added_by=None):
        """Add a student to the group"""
        if self.is_full:
            raise ValueError(f"Group {self.name} is full")
        
        # Check if student is already in another active group
        existing_membership = GroupMembership.objects.filter(
            student=student,
            is_active=True
        ).exclude(group=self).first()
        
        if existing_membership:
            raise ValueError(f"Student is already in group {existing_membership.group.name}")
        
        # Create membership
        membership, created = GroupMembership.objects.get_or_create(
            group=self,
            student=student,
            defaults={'added_by': added_by}
        )
        
        if not created:
            # Reactivate if was previously inactive
            membership.is_active = True
            membership.joined_at = timezone.now()
            membership.save()
        
        # Log activity
        GroupActivity.objects.create(
            group=self,
            action='student_added',
            user=added_by,
            details=f'{student.display_name} added to group'
        )
        
        return membership
    
    def remove_student(self, student, removed_by=None):
        """Remove a student from the group"""
        try:
            membership = GroupMembership.objects.get(
                group=self,
                student=student,
                is_active=True
            )
            membership.is_active = False
            membership.left_at = timezone.now()
            membership.save()
            
            # Log activity
            GroupActivity.objects.create(
                group=self,
                action='student_removed',
                user=removed_by,
                details=f'{student.display_name} removed from group'
            )
            
            return True
        except GroupMembership.DoesNotExist:
            return False


class GroupMembership(models.Model):
    """Many-to-many relationship between students and groups"""
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        limit_choices_to={'role': 'student'}
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    # Who added the student
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students_added'
    )
    
    class Meta:
        ordering = ['joined_at']
        unique_together = ['group', 'student']
        indexes = [
            models.Index(fields=['student', 'is_active']),
            models.Index(fields=['group', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.display_name} in {self.group.name}"


class GroupActivity(models.Model):
    """Track activities within a group"""
    
    ACTION_CHOICES = [
        ('created', 'Group Created'),
        ('updated', 'Group Updated'),
        ('student_added', 'Student Added'),
        ('student_removed', 'Student Removed'),
        ('supervisor_changed', 'Supervisor Changed'),
        ('group_started', 'Group Started'),
        ('group_completed', 'Group Completed'),
    ]
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Group activities'
    
    def __str__(self):
        return f"{self.group.name} - {self.get_action_display()}"