# File: dashboard/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse 
from accounts.models import User, UserProfile
from projects.models import Project, ProjectDeliverable, ProjectActivity
from groups.models import Group, GroupMembership
from analytics.models import StressLevel
from analytics.calculators import DashboardCalculator  

@login_required
def dashboard_home(request):
    """Redirect to appropriate dashboard based on user role"""
    user = request.user
    
    # Check active role from session or user model
    active_role = request.session.get('active_role') or user.role
    
    # Superusers are treated as admins
    if user.is_superuser or active_role == 'admin':
        return redirect('dashboard:admin_dashboard')
    elif active_role == 'supervisor':
        return redirect('dashboard:supervisor_dashboard')
    elif active_role == 'student':
        return redirect('dashboard:student_dashboard')
    else:
        messages.error(request, 'No valid role assigned.')
        return redirect('accounts:login')


@login_required
def admin_dashboard(request):
    """Admin dashboard - UPDATED for new User model with REAL chart data"""
    
    user = request.user
    
    # Check permissions - allow superusers and admin roles
    if not (user.is_superuser or user.is_admin):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    # Get users with visible initial passwords
    users_with_passwords = User.objects.filter(
        initial_password_visible=True,
        is_superuser=False
    ).exclude(id=request.user.id)
    
    # User statistics
    total_users = User.objects.exclude(is_superuser=True).count()
    students_count = User.objects.filter(role='student').count()
    supervisors_count = User.objects.filter(role='supervisor').count()
    admins_count = User.objects.filter(role='admin').count()
    
    # Recent activity - users created in last 7 days
    recent_users = User.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).exclude(is_superuser=True).order_by('-created_at')[:5]
    
    # NEW: Get REAL chart data for dashboard
    weekly_activity_data = DashboardCalculator.get_weekly_activity_data()
    user_distribution_data = DashboardCalculator.get_user_distribution_data()
    system_health_metrics = DashboardCalculator.get_system_health_metrics()
    
    context = {
        'title': 'Admin Dashboard - PrimeTime',
        
        # User statistics - UPDATED
        'total_users': total_users,
        'pending_users': users_with_passwords.count(),
        'students_count': students_count,
        'supervisors_count': supervisors_count,
        'admins_count': admins_count,
        
        # Project statistics
        'pending_projects': Project.objects.filter(status='pending').count(),
        'approved_projects': Project.objects.filter(status='approved').count(),
        'completed_projects': Project.objects.filter(status='completed').count(),
        'in_progress_projects': Project.objects.filter(status='in_progress').count(),
        
        # User management - UPDATED
        'users_with_passwords': users_with_passwords,
        'recent_users': recent_users,
        'pending_projects_list': Project.objects.filter(
            status='pending'
        ).select_related('student')[:5],
        
        # Batch data
        'current_batch': timezone.now().year,
        'active_batches': Project.objects.values_list(
            'batch_year', flat=True
        ).distinct(),
        
        # Role context
        'is_admin': user.is_admin,
        'is_superuser': user.is_superuser,
        
        # NEW: REAL CHART DATA
        'weekly_activity_data': weekly_activity_data,
        'user_distribution_data': user_distribution_data,
        'system_health_metrics': system_health_metrics,
    }
    
    return render(request, 'dashboard/admin/home_enhanced.html', context)  # Use enhanced template


@login_required
def student_dashboard(request):
    """Student dashboard with project status and progress - UPDATED with strict stress validation"""
    
    if not request.user.is_student:
        messages.error(request, 'Access denied. Students only.')
        return redirect('dashboard:home')
    
    student = request.user
    
    # Get or create student's project for current batch
    current_batch = timezone.now().year
    try:
        project = Project.objects.get(
            student=student,
            batch_year=current_batch
        )
    except Project.DoesNotExist:
        project = None
    
    # Get group membership
    try:
        group_membership = GroupMembership.objects.get(
            student=student,
            is_active=True
        )
        group = group_membership.group
    except GroupMembership.DoesNotExist:
        group = None
    
    # STRICT STRESS LEVEL CALCULATION - Only show if meaningful data exists
    stress_level = 0
    has_stress_data = False
    
    # Get latest stress level
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()
    if latest_stress and latest_stress.level > 10:
        stress_level = latest_stress.level
        has_stress_data = True
    else:
        # No meaningful stress data available
        stress_level = 0
        has_stress_data = False
    
    # Calculate progress
    progress = project.progress_percentage if project else 0
    
    # Get upcoming deadlines
    upcoming_deadlines = []
    if project and project.status in ['approved', 'in_progress']:
        upcoming_deadlines = [
            {'name': 'Mid Defense', 'date': timezone.now() + timedelta(days=14)},
            {'name': 'Pre Defense', 'date': timezone.now() + timedelta(days=30)},
        ]
    
    # Recent activities
    recent_activities = ProjectActivity.objects.filter(
        project=project
    ).order_by('-timestamp')[:5]
    
    # Student-specific stats - UPDATED with new fields
    context = {
        'title': 'Student Dashboard - PrimeTime',
        'project': project,
        'group': group,
        'progress': progress,
        'stress_level': stress_level,
        'has_stress_data': has_stress_data,
        'upcoming_deadlines': upcoming_deadlines,
        'recent_activities': recent_activities,
        
        # Quick stats
        'deliverables_submitted': ProjectDeliverable.objects.filter(
            project=project
        ).count() if project else 0,
        'deliverables_approved': ProjectDeliverable.objects.filter(
            project=project,
            is_approved=True
        ).count() if project else 0,
        
        # Student info from new fields - UPDATED
        'student_id': student.user_id,
        'department': student.department,
        'enrollment_year': student.enrollment_year,
        'batch_year': student.batch_year,
        
        # Feedback count (placeholder)
        'feedback_count': 0,
    }
    
    return render(request, 'dashboard/student/home.html', context)


@login_required
def supervisor_dashboard(request):
    """Supervisor dashboard with group management - UPDATED"""
    
    if not request.user.is_supervisor:
        messages.error(request, 'Access denied. Supervisors only.')
        return redirect('dashboard:home')
    
    supervisor = request.user
    
    # Get supervisor's groups
    supervised_groups = Group.objects.filter(
        supervisor=supervisor,
        is_active=True
    ).prefetch_related('members')
    
    # Get all supervised students
    supervised_students = User.objects.filter(
        group_memberships__group__supervisor=supervisor,
        group_memberships__is_active=True
    ).distinct()
    
    # Get projects needing review
    projects_to_review = Project.objects.filter(
        supervisor=supervisor,
        status='in_progress'
    ).select_related('student')
    
    # Get pending deliverables
    pending_deliverables = ProjectDeliverable.objects.filter(
        project__supervisor=supervisor,
        is_approved=False
    ).select_related('project', 'project__student')
    
    # Calculate statistics
    total_students = supervised_students.count()
    avg_progress = Project.objects.filter(
        supervisor=supervisor,
        status__in=['in_progress', 'completed']
    ).aggregate(Avg('progress_percentage'))['progress_percentage__avg'] or 0
    
    # Students with high stress (placeholder)
    high_stress_students = []
    
    # Recent submissions
    recent_submissions = ProjectDeliverable.objects.filter(
        project__supervisor=supervisor
    ).order_by('-submitted_at')[:5]
    
    # Supervisor profile info - UPDATED
    try:
        supervisor_profile = UserProfile.objects.get(user=supervisor)
        max_groups = supervisor_profile.max_groups
        specialization = supervisor_profile.specialization
    except UserProfile.DoesNotExist:
        max_groups = 3
        specialization = ""
    
    context = {
        'title': 'Supervisor Dashboard - PrimeTime',
        'supervised_groups': supervised_groups,
        'supervised_students': supervised_students,
        'projects_to_review': projects_to_review,
        'pending_deliverables': pending_deliverables,
        
        # Statistics
        'total_groups': supervised_groups.count(),
        'total_students': total_students,
        'avg_progress': round(avg_progress, 1),
        'pending_reviews': pending_deliverables.count(),
        
        'high_stress_students': high_stress_students,
        'recent_submissions': recent_submissions,
        
        # Supervisor info from new fields - UPDATED
        'supervisor_profile': supervisor_profile,
        'max_groups': max_groups,
        'specialization': specialization,
        'department': supervisor.department,
    }
    
    return render(request, 'dashboard/supervisor/home.html', context)


@login_required
def switch_role(request):
    """Allow users to switch between roles if they have multiple roles"""

    if request.method == 'POST':
        new_role = request.POST.get('role')
        user = request.user

        valid_roles = ['admin', 'supervisor', 'student']

        if new_role not in valid_roles:
            messages.error(request, 'Invalid role selected')
            return redirect('dashboard:home')

        # Check permission
        if (user.is_superuser and new_role in ['admin', 'supervisor']) or \
           (hasattr(user, 'role') and user.role == new_role) or \
           (user.is_admin and new_role == 'admin'):
            
            request.session['active_role'] = new_role
            messages.success(request, f'Switched to {new_role} role')

            if new_role == 'admin':
                return redirect('dashboard:admin_dashboard')
            elif new_role == 'supervisor':
                return redirect('dashboard:supervisor_dashboard')
            elif new_role == 'student':
                return redirect('dashboard:student_dashboard')
        else:
            messages.error(request, 'You do not have permission for this role')

    return redirect('dashboard:home')


@login_required
def user_profile(request):
    """User profile page showing both User and UserProfile data - UPDATED"""
    
    user = request.user
    
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    context = {
        'title': 'My Profile - PrimeTime',
        'user': user,
        'profile': profile,
        
        # New fields
        'user_id': user.user_id,
        'full_name': user.full_name,
        'department': user.department,
        'enrollment_year': user.enrollment_year,
        'batch_year': user.batch_year,
        
        # Password info
        'password_changed': user.password_changed,
        'must_change_password': user.must_change_password,
        'initial_password_visible': user.initial_password_visible,
        'password_changed_at': user.password_changed_at,
        
        # Account info
        'last_login_at': user.last_login_at,
        'created_at': user.created_at,
        'is_enabled': user.is_enabled,
    }
    
    return render(request, 'accounts/profile.html', context)


# NEW: API endpoint for system health data
@login_required
def system_health_api(request):
    """API endpoint for system health metrics (AJAX)"""
    if not request.user.is_admin and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        system_health_metrics = DashboardCalculator.get_system_health_metrics()
        return JsonResponse(system_health_metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)