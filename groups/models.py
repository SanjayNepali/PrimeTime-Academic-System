# File: Desktop/Prime/groups/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import User


class Group(models.Model):
    """Project groups with supervisor and students"""
    
    name = models.CharField(max_length=100)
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='supervised_groups',
        limit_choices_to={'role': 'supervisor'}
    )
    batch_year = models.IntegerField()
    
    # Group settings
    max_students = models.IntegerField(default=7)
    min_students = models.IntegerField(default=5)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_full = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups'
    )
    
    class Meta:
        ordering = ['-batch_year', 'name']
        unique_together = ['name', 'batch_year']
    
    def __str__(self):
        return f"{self.name} ({self.batch_year}) - {self.supervisor.get_full_name()}"
    
    @property
    def student_count(self):
        """Get current number of students in group"""
        return self.members.filter(is_active=True).count()
    
    @property
    def available_slots(self):
        """Get number of available slots"""
        return self.max_students - self.student_count
    
    def add_student(self, student):
        """Add a student to the group"""
        if self.is_full:
            raise ValidationError("Group is already full")
        
        if student.role != 'student':
            raise ValidationError("Only students can be added to groups")
        
        # Check if student already in a group
        existing = GroupMembership.objects.filter(
            student=student,
            is_active=True
        ).exists()
        
        if existing:
            raise ValidationError("Student is already in another group")
        
        membership = GroupMembership.objects.create(
            group=self,
            student=student
        )
        
        # Update full status
        if self.student_count >= self.max_students:
            self.is_full = True
            self.save()
        
        return membership
    
    def remove_student(self, student):
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
            
            # Update full status
            if self.is_full and self.student_count < self.max_students:
                self.is_full = False
                self.save()
                
        except GroupMembership.DoesNotExist:
            raise ValidationError("Student not in this group")
    
    def can_start(self):
        """Check if group has minimum students to start"""
        return self.student_count >= self.min_students


class GroupMembership(models.Model):
    """Track student membership in groups"""
    
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
    
    class Meta:
        ordering = ['-joined_at']
        unique_together = ['group', 'student']
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.student.get_full_name()} in {self.group.name} ({status})"


class GroupActivity(models.Model):
    """Track group-related activities"""
    
    ACTION_CHOICES = [
        ('created', 'Group Created'),
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
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Group activities'
    
    def __str__(self):
        return f"{self.group.name} - {self.get_action_display()}"