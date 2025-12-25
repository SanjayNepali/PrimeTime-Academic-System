# File: dashboard/views.py - COMPLETE FIXED VERSION

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
    """Admin dashboard with accurate counts"""
    
    user = request.user
    
    # Check permissions
    if not (user.is_superuser or user.is_admin):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    # Get users with visible initial passwords
    users_with_passwords = User.objects.filter(
        initial_password_visible=True,
        is_superuser=False
    ).exclude(id=request.user.id)
    
    # User statistics
    total_users = User.objects.filter(is_superuser=False).count()
    students_count = User.objects.filter(role='student').count()
    supervisors_count = User.objects.filter(role='supervisor').count()
    admins_count = User.objects.filter(role='admin').count()
    
    # Recent activity
    week_ago = timezone.now() - timedelta(days=7)
    recent_users_count = User.objects.filter(
        created_at__gte=week_ago,
        is_superuser=False
    ).count()
    
    recent_users = User.objects.filter(
        created_at__gte=week_ago,
        is_superuser=False
    ).order_by('-created_at')[:5]
    
    # Project statistics
    pending_projects_count = Project.objects.filter(status='pending').count()
    approved_projects_count = Project.objects.filter(status='approved').count()
    completed_projects_count = Project.objects.filter(status='completed').count()
    in_progress_projects_count = Project.objects.filter(status='in_progress').count()
    
    pending_projects_list = Project.objects.filter(
        status='pending'
    ).select_related('student')[:5]
    
    # Get chart data
    weekly_activity_data = DashboardCalculator.get_weekly_activity_data()
    user_distribution_data = DashboardCalculator.get_user_distribution_data()
    system_health_metrics = DashboardCalculator.get_system_health_metrics()
    
    context = {
        'title': 'Admin Dashboard - PrimeTime',
        
        # User statistics
        'total_users': total_users,
        'pending_users': users_with_passwords.count(),
        'students_count': students_count,
        'supervisors_count': supervisors_count,
        'admins_count': admins_count,
        
        # Project statistics
        'pending_projects': pending_projects_count,
        'approved_projects': approved_projects_count,
        'completed_projects': completed_projects_count,
        'in_progress_projects': in_progress_projects_count,
        
        # User management
        'users_with_passwords': users_with_passwords,
        'recent_users': recent_users,
        'recent_users_count': recent_users_count,
        'pending_projects_list': pending_projects_list,
        
        # Chart data
        'weekly_activity_data': weekly_activity_data,
        'user_distribution_data': user_distribution_data,
        'system_health_metrics': system_health_metrics,
        
        # Role context
        'is_admin': user.is_admin,
        'is_superuser': user.is_superuser,
    }
    
    return render(request, 'dashboard/admin/home_enhanced.html', context)


@login_required
def student_dashboard(request):
    """Student dashboard with project status and progress"""
    
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
    
    # Stress level calculation
    stress_level = 0
    has_stress_data = False
    
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()
    if latest_stress and latest_stress.level > 10:
        stress_level = latest_stress.level
        has_stress_data = True
    
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
    recent_activities = []
    if project:
        recent_activities = ProjectActivity.objects.filter(
            project=project
        ).order_by('-timestamp')[:5]
    
    context = {
        'title': 'Student Dashboard - PrimeTime',
        'project': project,
        'group': group,
        'progress': progress,
        'stress_level': stress_level,
        'has_stress_data': has_stress_data,
        'latest_stress': latest_stress,
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
        
        # Student info
        'student_id': student.user_id,
        'department': student.department,
        'enrollment_year': student.enrollment_year,
        'batch_year': student.batch_year,
        
        'feedback_count': 0,
    }
    
    return render(request, 'dashboard/student/home.html', context)


@login_required
def supervisor_dashboard(request):
    """Supervisor dashboard with group management - COMPLETELY FIXED"""
    
    if not request.user.is_supervisor:
        messages.error(request, 'Access denied. Supervisors only.')
        return redirect('dashboard:home')
    
    supervisor = request.user
    
    # Get supervisor's groups - FIXED QUERY
    supervised_groups = Group.objects.filter(
        supervisor=supervisor,
        is_active=True
    ).annotate(
        student_count=Count('members', filter=Q(members__is_active=True))
    ).prefetch_related('members__student')
    
    # Get all supervised students - FIXED QUERY
    supervised_students = User.objects.filter(
        group_memberships__group__supervisor=supervisor,
        group_memberships__is_active=True,
        role='student'
    ).distinct().prefetch_related('projects')
    
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
    
    # Calculate average progress from actual projects
    avg_progress = 0
    if total_students > 0:
        projects_with_progress = Project.objects.filter(
            supervisor=supervisor,
            status__in=['in_progress', 'completed']
        )
        if projects_with_progress.exists():
            avg_progress = projects_with_progress.aggregate(
                Avg('progress_percentage')
            )['progress_percentage__avg'] or 0
    
    # Get high stress students - FIXED QUERY
    high_stress_students = []
    for student in supervised_students[:10]:
        try:
            latest_stress = StressLevel.objects.filter(
                student=student
            ).order_by('-calculated_at').first()
            
            if latest_stress and latest_stress.level >= 60:
                student.stress_level = latest_stress.level
                high_stress_students.append(student)
        except Exception:
            continue
    
    # Recent submissions
    recent_submissions = ProjectDeliverable.objects.filter(
        project__supervisor=supervisor
    ).order_by('-submitted_at')[:5]
    
    # Supervisor profile info
    try:
        supervisor_profile = UserProfile.objects.get(user=supervisor)
        max_groups = supervisor_profile.max_groups
        specialization = supervisor_profile.specialization
    except UserProfile.DoesNotExist:
        supervisor_profile = None
        max_groups = 3
        specialization = ""
    
    # Add stress levels to supervised students for display
    for student in supervised_students[:20]:
        try:
            latest_stress = StressLevel.objects.filter(
                student=student
            ).order_by('-calculated_at').first()
            student.stress_level = latest_stress.level if latest_stress else 0
        except Exception:
            student.stress_level = 0
    
    context = {
        'title': 'Supervisor Dashboard - PrimeTime',
        'supervised_groups': supervised_groups,
        'supervised_students': supervised_students,
        'projects_to_review': projects_to_review,
        'pending_deliverables': pending_deliverables,
        
        # Statistics - FIXED
        'total_groups': supervised_groups.count(),
        'total_students': total_students,
        'avg_progress': round(avg_progress, 1),
        'pending_reviews': pending_deliverables.count(),
        
        'high_stress_students': high_stress_students,
        'recent_submissions': recent_submissions,
        
        # Supervisor info
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
    """User profile page showing both User and UserProfile data"""
    
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

@login_required
def student_stress_api(request, student_id):
    """Return latest stress level for a student (AJAX API)"""

    # Permission check
    if not (
        request.user.is_admin or
        request.user.is_superuser or
        request.user.is_supervisor or
        request.user.user_id == student_id
    ):
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        student = User.objects.get(user_id=student_id, role='student')
    except User.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

    latest_stress = StressLevel.objects.filter(
        student=student
    ).order_by('-calculated_at').first()

    if not latest_stress:
        return JsonResponse({
            'student_id': student_id,
            'stress_level': 0,
            'has_data': False
        })

    return JsonResponse({
        'student_id': student_id,
        'stress_level': latest_stress.level,
        'has_data': True,
        'calculated_at': latest_stress.calculated_at
    })
@login_required
def supervisor_metrics_api(request):
    """Return dashboard metrics for supervisor (AJAX API)"""

    if not request.user.is_supervisor:
        return JsonResponse({'error': 'Access denied'}, status=403)

    supervisor = request.user

    total_students = User.objects.filter(
        group_memberships__group__supervisor=supervisor,
        group_memberships__is_active=True,
        role='student'
    ).distinct().count()

    total_projects = Project.objects.filter(
        supervisor=supervisor
    ).count()

    pending_deliverables = ProjectDeliverable.objects.filter(
        project__supervisor=supervisor,
        is_approved=False
    ).count()

    avg_progress = Project.objects.filter(
        supervisor=supervisor,
        status__in=['in_progress', 'completed']
    ).aggregate(
        Avg('progress_percentage')
    )['progress_percentage__avg'] or 0

    return JsonResponse({
        'total_students': total_students,
        'total_projects': total_projects,
        'pending_deliverables': pending_deliverables,
        'avg_progress': round(avg_progress, 1),
    })
