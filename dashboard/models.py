# File: Desktop/Prime/dashboard/models.py

from django.db import models
from django.utils import timezone
from accounts.models import User


class DashboardStats(models.Model):
    """Track dashboard statistics for analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    
    # Admin stats
    total_users = models.IntegerField(default=0)
    pending_users = models.IntegerField(default=0)
    pending_projects = models.IntegerField(default=0)
    
    # Student stats
    project_progress = models.FloatField(default=0.0)
    stress_level = models.FloatField(default=0.0)
    
    # Supervisor stats
    active_groups = models.IntegerField(default=0)
    students_supervised = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
