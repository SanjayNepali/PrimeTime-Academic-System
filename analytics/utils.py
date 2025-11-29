# File: analytics/utils.py

from django.utils import timezone
from django.db.models import Q
from .models import SystemActivity

def log_system_activity(activity_type, description, user=None, target_user=None, project=None, metadata=None, check_duplicates=True):
    """
    Log system activity for admin dashboard
    
    Args:
        activity_type: One of the ACTIVITY_TYPES choices
        description: Human-readable description of the activity
        user: User who performed the action (optional)
        target_user: User who was targeted by the action (optional)
        project: Related project (optional)
        metadata: Additional context data as dict (optional)
        check_duplicates: Whether to check for recent duplicates (default: True)
    """
    try:
        # Check for recent duplicates (within last 5 minutes) to avoid spam
        if check_duplicates:
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
            duplicate = SystemActivity.objects.filter(
                activity_type=activity_type,
                description=description,
                user=user,
                timestamp__gte=five_minutes_ago
            ).exists()
            
            if duplicate:
                return False  # Skip logging duplicate
        
        SystemActivity.objects.create(
            activity_type=activity_type,
            description=description,
            user=user,
            target_user=target_user,
            project=project,
            metadata=metadata or {}
        )
        return True
    except Exception as e:
        # Log the error but don't break the main functionality
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log system activity: {e}")
        return False

# Specific activity logging functions for common scenarios
def log_stress_analysis(student, stress_level, category):
    """Log stress analysis activity - only log significant changes"""
    # Only log if stress level is moderate or high, or if it's a significant change
    if stress_level < 40:  # Don't log low stress levels
        return False
        
    return log_system_activity(
        activity_type='stress_analysis',
        description=f"Stress analysis: {student.display_name} - {stress_level:.1f}% ({category})",
        user=student,
        target_user=student,
        metadata={
            'stress_level': stress_level,
            'category': category,
            'student_id': student.id
        }
    )

def log_feedback_added(supervisor, student, rating, action_required):
    """Log supervisor feedback activity"""
    action_text = " - Action Required" if action_required else ""
    rating_text = f" (Rating: {rating}/5)" if rating else " (No rating)"
    
    return log_system_activity(
        activity_type='feedback_added',
        description=f"Feedback for {student.display_name}{rating_text}{action_text}",
        user=supervisor,
        target_user=student,
        metadata={
            'rating': rating,
            'action_required': action_required,
            'supervisor_id': supervisor.id,
            'student_id': student.id
        }
    )

def log_meeting_logged(supervisor, student, duration, meeting_type):
    """Log supervisor meeting activity"""
    return log_system_activity(
        activity_type='meeting_logged',
        description=f"Meeting: {supervisor.display_name} with {student.display_name} - {duration}min {meeting_type}",
        user=supervisor,
        target_user=student,
        metadata={
            'duration': duration,
            'meeting_type': meeting_type,
            'supervisor_id': supervisor.id,
            'student_id': student.id
        }
    )

def log_project_created(student, project_title):
    """Log project creation activity"""
    from projects.models import Project
    try:
        project = Project.objects.get(student=student, title=project_title)
    except Project.DoesNotExist:
        project = None
        
    return log_system_activity(
        activity_type='project_created',
        description=f"New project: {project_title} by {student.display_name}",
        user=student,
        target_user=student,
        project=project,
        metadata={
            'project_title': project_title,
            'student_id': student.id
        }
    )

def log_deliverable_submitted(student, deliverable_stage):
    """Log deliverable submission activity"""
    return log_system_activity(
        activity_type='deliverable_submitted',
        description=f"Deliverable submitted: {student.display_name} - {deliverable_stage}",
        user=student,
        target_user=student,
        metadata={
            'deliverable_stage': deliverable_stage,
            'student_id': student.id
        }
    )

def log_deliverable_approved(student, deliverable_stage, approved_by):
    """Log deliverable approval activity"""
    return log_system_activity(
        activity_type='deliverable_approved',
        description=f"Deliverable approved: {student.display_name} - {deliverable_stage} by {approved_by.display_name}",
        user=approved_by,
        target_user=student,
        metadata={
            'deliverable_stage': deliverable_stage,
            'student_id': student.id,
            'approved_by_id': approved_by.id
        }
    )

def log_user_created(admin_user, new_user):
    """Log user creation activity"""
    return log_system_activity(
        activity_type='user_created',
        description=f"New user: {new_user.display_name} ({new_user.role}) created by {admin_user.display_name}",
        user=admin_user,
        target_user=new_user,
        metadata={
            'new_user_role': new_user.role,
            'new_user_id': new_user.id
        }
    )

def log_user_login(user):
    """Log user login activity (only for significant logins)"""
    # Only log first logins or admin/supervisor logins, not every login
    if not user.password_changed or user.role in ['admin', 'supervisor']:
        return log_system_activity(
            activity_type='user_login',
            description=f"User login: {user.display_name} ({user.role})",
            user=user,
            metadata={
                'user_role': user.role,
                'user_id': user.id
            },
            check_duplicates=True  # Prevent multiple login logs for same user
        )
    return False

def log_analytics_run(user, analytics_type):
    """Log analytics run activity - only for significant runs"""
    # Don't log every dashboard view, only manual analytics runs
    if analytics_type in ['manual_stress_analysis', 'batch_processing', 'system_report']:
        return log_system_activity(
            activity_type='analytics_run',
            description=f"Analytics: {user.display_name} ran {analytics_type}",
            user=user,
            metadata={
                'analytics_type': analytics_type,
                'user_role': user.role
            }
        )
    return False

def log_high_stress_alert(student, stress_level, previous_level=None):
    """Log high stress alerts"""
    trend = ""
    if previous_level:
        if stress_level > previous_level + 10:
            trend = " 📈"
        elif stress_level < previous_level - 10:
            trend = " 📉"
    
    return log_system_activity(
        activity_type='stress_analysis',
        description=f"🚨 High stress alert: {student.display_name} - {stress_level:.1f}%{trend}",
        user=student,
        target_user=student,
        metadata={
            'stress_level': stress_level,
            'previous_level': previous_level,
            'student_id': student.id,
            'is_alert': True
        }
    )

def log_group_activity(supervisor, group_name, activity_type, description):
    """Log group-related activities"""
    activity_map = {
        'group_created': 'Group Created',
        'student_added': 'Student Added to Group',
        'student_removed': 'Student Removed from Group',
    }
    
    return log_system_activity(
        activity_type=activity_type,
        description=f"Group: {group_name} - {description}",
        user=supervisor,
        metadata={
            'group_name': group_name,
            'activity_type': activity_type
        }
    )