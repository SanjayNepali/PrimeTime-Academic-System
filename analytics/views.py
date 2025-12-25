# File: analytics/views.py 

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta

from .models import StressLevel, SupervisorFeedback, SupervisorMeetingLog, SystemActivity
from .sentiment import AdvancedSentimentAnalyzer
from .calculators import StressCalculator, PerformanceCalculator, AnalyticsDashboard
from .forms import SupervisorFeedbackForm
from accounts.models import User
# FIXED: Import ProjectActivity instead of ProjectProgress
from projects.models import Project, ProjectActivity, ProjectLogSheet, GroupMeeting  # CHANGED SupervisorMeeting to GroupMeeting
# Add at the top of analytics/views.py
from .utils import (
    log_stress_analysis, log_feedback_added, log_meeting_logged,
    log_analytics_run, log_system_activity, log_high_stress_alert
)
from groups.models import GroupMembership
from chat.models import Message


@login_required
def my_analytics(request):
    """Student view of their own analytics - ONLY REAL DATA"""
    if request.user.role != 'student':
        messages.error(request, "This page is for students only")
        return redirect('dashboard:home')

    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest_stress = StressLevel.objects.filter(student=request.user).order_by('-calculated_at').first()
    
    # Only calculate trends if we have actual data
    stress_trend = None
    stress_history = None
    if latest_stress:
        stress_trend = StressCalculator.get_stress_trend(request.user, days=30)
        # FIXED: Use 'calculated_at' instead of 'timestamp'
        stress_history = StressLevel.objects.filter(student=request.user).order_by('-calculated_at')[:10]
    
    # Only calculate performance if project exists
    performance = None
    try:
        project = Project.objects.get(student=request.user)
        performance = PerformanceCalculator.calculate_student_performance(request.user)
    except Project.DoesNotExist:
        performance = None

    context = {
        'latest_stress': latest_stress,  # Will be None if no analysis run
        'stress_trend': stress_trend,    # Will be None if no stress data
        'performance': performance,      # Will be None if no project
        'stress_history': stress_history, # Will be None if no stress data
        'has_data': bool(latest_stress), # Explicit flag for template
    }
    return render(request, 'analytics/my_analytics.html', context)


@login_required
def supervisor_analytics(request):
    """Supervisor view of their groups' analytics"""
    if request.user.role != 'supervisor':
        messages.error(request, "This page is for supervisors only")
        return redirect('dashboard:home')

    analytics = AnalyticsDashboard.get_supervisor_analytics(request.user)

    context = {
        'analytics': analytics,
    }
    return render(request, 'analytics/supervisor_analytics.html', context)


@login_required
def admin_analytics(request):
    """Admin view of system-wide analytics"""
    if request.user.role != 'admin':
        messages.error(request, "This page is for administrators only")
        return redirect('dashboard:home')

    analytics = AnalyticsDashboard.get_admin_analytics()

    # DON'T log every dashboard view - too noisy!
    # Only log if it's the first view today or if there are important alerts
    from datetime import date
    today = date.today()
    
    # Check if we've already logged today's first view
    from .models import SystemActivity
    today_views = SystemActivity.objects.filter(
        activity_type='analytics_run',
        user=request.user,
        timestamp__date=today
    ).exists()
    
    if not today_views:
        from .utils import log_system_activity
        log_system_activity(
            activity_type='analytics_run',
            description=f"Admin dashboard viewed by {request.user.display_name}",
            user=request.user,
            check_duplicates=False
        )

    # Get recent system activities - exclude noisy analytics_run entries
    recent_activities = SystemActivity.objects.select_related(
        'user', 'target_user', 'project'
    ).exclude(
        activity_type='analytics_run'  # Exclude analytics run entries
    ).order_by('-timestamp')[:25]

    context = {
        'analytics': analytics,
        'recent_activities': recent_activities,
        'now': timezone.now(),
    }
    return render(request, 'analytics/admin_analytics.html', context)

@login_required
def student_stress_detail(request, student_id):
    """Detailed stress view for a specific student (supervisor/admin only)"""
    if request.user.role not in ['admin', 'supervisor']:
        messages.error(request, "You don't have permission to view this page")
        return redirect('dashboard:home')

    student = get_object_or_404(User, pk=student_id, role='student')

    # If supervisor, check if they supervise this student
    if request.user.role == 'supervisor':
        is_supervisor = GroupMembership.objects.filter(
            student=student,
            group__supervisor=request.user,
            is_active=True
        ).exists()

        if not is_supervisor:
            messages.error(request, "You are not the supervisor for this student")
            return redirect('analytics:supervisor_analytics')

    # Get comprehensive stress data - only if exists
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()
    stress_trend = None
    stress_history = None
    
    if latest_stress:
        stress_trend = StressCalculator.get_stress_trend(student, days=60)
        # FIXED: Use 'calculated_at' instead of 'timestamp'
        stress_history = StressLevel.objects.filter(student=student).order_by('-calculated_at')[:20]

    context = {
        'student': student,
        'latest_stress': latest_stress,
        'stress_trend': stress_trend,
        'stress_history': stress_history,
    }
    return render(request, 'analytics/student_stress_detail.html', context)

@login_required
def run_stress_analysis(request):
    """Manually trigger stress analysis for current user"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Only students can run stress analysis'}, status=403)

    try:
        analyzer = AdvancedSentimentAnalyzer(request.user)
        stress_record = analyzer.comprehensive_stress_analysis(days=7)

        # FIXED: Handle the case when no data is available
        if stress_record is None:
            return JsonResponse({
                'success': False,
                'message': 'Not enough data available for stress analysis. Please ensure you have a project with deliverables and some chat activity.'
            })

        # Log the stress analysis activity (only if significant)
        from .utils import log_stress_analysis, log_high_stress_alert
        
        # Get previous stress level to detect trends
        from .models import StressLevel
        # FIXED: Use 'calculated_at' instead of 'timestamp'
        previous_stress = StressLevel.objects.filter(
            student=request.user
        ).exclude(id=stress_record.id).order_by('-calculated_at').first()
        
        # Log high stress alerts
        if stress_record.level >= 70:
            log_high_stress_alert(
                student=request.user,
                stress_level=stress_record.level,
                previous_level=previous_stress.level if previous_stress else None
            )
        else:
            # Only log moderate/high stress, not low stress
            log_stress_analysis(
                student=request.user,
                stress_level=stress_record.level,
                category=stress_record.stress_category
            )

        return JsonResponse({
            'success': True,
            'stress_level': stress_record.level,
            'category': stress_record.stress_category,
            'message': f'Your current stress level is {stress_record.level:.1f}% ({stress_record.stress_category})'
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Stress analysis error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    
# ========== SUPERVISOR STUDENT MONITORING VIEWS ==========

@login_required
def supervisor_view_student_profile(request, student_id):
    """Supervisor view of student profile with stress, progress, and log sheet"""
    if request.user.role != 'supervisor':
        messages.error(request, "Only supervisors can access this page")
        return redirect('dashboard:home')

    student = get_object_or_404(User, pk=student_id, role='student')

    # Check if supervisor supervises this student
    is_supervisor = GroupMembership.objects.filter(
        student=student,
        group__supervisor=request.user,
        is_active=True
    ).exists()

    if not is_supervisor:
        messages.error(request, "You are not the supervisor for this student")
        return redirect('dashboard:home')

    # Get student's project
    try:
        project = Project.objects.get(student=student)
    except Project.DoesNotExist:
        project = None

    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()

    # Get stress trend (last 30 days) - only if stress data exists
    stress_history = None
    if latest_stress:
        # FIXED: Use 'calculated_at' instead of 'timestamp'
        stress_history = StressLevel.objects.filter(student=student).order_by('-calculated_at')[:30]

    # FIXED: Use project.progress_percentage directly
    latest_progress = None
    if project:
        latest_progress = {
            'percentage': project.progress_percentage,
            'timestamp': project.updated_at,
            'project': project
        }

    # Get supervisor feedback log sheet
    feedback_list = SupervisorFeedback.objects.filter(
        student=student,
        supervisor=request.user
    ).order_by('-date')[:20]

    # Get recent meetings
    recent_meetings = SupervisorMeetingLog.objects.filter(
        student=student,
        supervisor=request.user
    ).order_by('-meeting_date')[:10]

    # Calculate average rating - only if ratings exist
    avg_rating = SupervisorFeedback.objects.filter(
        student=student,
        supervisor=request.user,
        rating__isnull=False
    ).aggregate(Avg('rating'))['rating__avg']

    context = {
        'student': student,
        'project': project,
        'latest_stress': latest_stress,
        'stress_history': stress_history,
        'latest_progress': latest_progress,
        'feedback_list': feedback_list,
        'recent_meetings': recent_meetings,
        'avg_rating': avg_rating,
    }
    return render(request, 'analytics/supervisor_student_profile.html', context)


@login_required
def supervisor_add_feedback(request, student_id):
    """Supervisor adds feedback log sheet entry for a student"""
    if request.user.role != 'supervisor':
        messages.error(request, "Only supervisors can add feedback")
        return redirect('dashboard:home')

    student = get_object_or_404(User, pk=student_id, role='student')

    # Check if supervisor supervises this student
    is_supervisor = GroupMembership.objects.filter(
        student=student,
        group__supervisor=request.user,
        is_active=True
    ).exists()

    if not is_supervisor:
        messages.error(request, "You are not the supervisor for this student")
        return redirect('dashboard:home')

    # Get student's project
    try:
        project = Project.objects.get(student=student)
    except Project.DoesNotExist:
        messages.error(request, "Student doesn't have a project yet")
        return redirect('analytics:supervisor_view_student', student_id=student_id)

    if request.method == 'POST':
        form = SupervisorFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.supervisor = request.user
            feedback.project = project
            feedback.save()

            # Calculate sentiment
            feedback.calculate_sentiment()

            # Log the feedback activity
            log_feedback_added(
                supervisor=request.user,
                student=student,
                rating=feedback.rating,
                action_required=feedback.action_required
            )

            messages.success(request, f"Feedback added successfully for {student.display_name}")
            return redirect('analytics:supervisor_view_student', student_id=student_id)
    else:
        form = SupervisorFeedbackForm(initial={'date': timezone.now().date()})

    context = {
        'form': form,
        'student': student,
        'project': project,
    }
    return render(request, 'analytics/add_feedback.html', context)

@login_required
def student_view_feedback(request):
    """Student views their feedback log sheet from supervisor"""
    if request.user.role != 'student':
        messages.error(request, "Only students can view their feedback")
        return redirect('dashboard:home')

    # Get all visible feedback for this student
    feedback_list = SupervisorFeedback.objects.filter(
        student=request.user,
        is_visible_to_student=True
    ).order_by('-date')

    # Get student's project
    try:
        project = Project.objects.get(student=request.user)
    except Project.DoesNotExist:
        project = None

    context = {
        'feedback_list': feedback_list,
        'project': project,
    }
    return render(request, 'analytics/student_feedback_list.html', context)

# File: analytics/views.py
# Fix the debug_stress_calculation function

@login_required
def debug_stress_calculation(request):
    """Debug view to see stress calculation breakdown"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Students only'}, status=403)
    
    analyzer = AdvancedSentimentAnalyzer(request.user)
    
    # FIXED: Use 'sender' instead of 'user'
    has_chat_data = Message.objects.filter(sender=request.user).exists()
    has_project = bool(analyzer.project)
    
    # Run analysis manually to see breakdown
    stress_data = {
        'chat_sentiment': analyzer._analyze_chat_sentiment(7),
        'project_progress': analyzer._analyze_project_progress(),
        'deadline_pressure': analyzer._calculate_deadline_pressure(),
        'workload_assessment': analyzer._assess_workload(),
        'social_engagement': analyzer._analyze_social_engagement(7)
    }
    
    overall_stress = analyzer._calculate_comprehensive_stress(stress_data)
    
    return JsonResponse({
        'has_chat_data': has_chat_data,
        'has_project': has_project,
        'stress_breakdown': stress_data,
        'overall_stress': overall_stress,
        'project': str(analyzer.project) if analyzer.project else None
    })

@login_required
def admin_view_all_logsheets(request):
    """Admin views all supervisor feedback log sheets and stress levels"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can access this page")
        return redirect('dashboard:home')

    # Get all feedback log sheets
    all_feedback = SupervisorFeedback.objects.select_related(
        'student', 'supervisor', 'project'
    ).order_by('-date')[:100]

    # Get high stress students using the fixed method
    high_stress_students = StressCalculator.get_high_stress_students(threshold=70)
    
    # Since it returns a list, we can slice it directly
    high_stress_students = high_stress_students[:50]

    # Get students requiring action
    action_required_feedback = SupervisorFeedback.objects.filter(
        action_required=True
    ).select_related('student', 'supervisor').order_by('-date')[:20]

    # Statistics - handle cases where no data exists
    total_feedback_count = SupervisorFeedback.objects.count()
    
    avg_rating_result = SupervisorFeedback.objects.filter(
        rating__isnull=False
    ).aggregate(Avg('rating'))
    avg_rating = avg_rating_result['rating__avg']
    
    avg_stress_result = StressLevel.objects.aggregate(Avg('level'))
    avg_stress = avg_stress_result['level__avg']

    context = {
        'all_feedback': all_feedback,
        'high_stress_students': high_stress_students,
        'action_required_feedback': action_required_feedback,
        'total_feedback_count': total_feedback_count,
        'avg_rating': avg_rating,
        'avg_stress': avg_stress,
    }
    return render(request, 'analytics/admin_all_logsheets.html', context)

@login_required
def get_realtime_stress(request, student_id):
    """
    API endpoint to get real-time stress for a student
    Used by dashboard to show live updates
    """
    if request.user.role not in ['admin', 'supervisor']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        student = User.objects.get(id=student_id, role='student')
    except User.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
    # Get latest stress record
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest_stress = StressLevel.objects.filter(
        student=student
    ).order_by('-calculated_at').first()
    
    if latest_stress:
        return JsonResponse({
            'student_id': student.id,
            'student_name': student.display_name,
            'stress_level': latest_stress.level,
            'chat_sentiment': latest_stress.chat_sentiment_score,
            'deadline_pressure': latest_stress.deadline_pressure,
            'workload': latest_stress.workload_score,
            'social_isolation': latest_stress.social_isolation_score,
            'calculated_at': latest_stress.calculated_at.isoformat(),
            'status': 'high' if latest_stress.level >= 70 else 'medium' if latest_stress.level >= 40 else 'low'
        })
    else:
        return JsonResponse({
            'student_id': student.id,
            'student_name': student.display_name,
            'stress_level': None,
            'status': 'no_data',
            'message': 'No stress data available yet'
        })

@login_required
def supervisor_view_student_profile_fixed(request, student_id):
    """View detailed student analytics - COMPLETELY FIXED VERSION"""
    
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can access this page.')
        return redirect('dashboard:home')
    
    student = get_object_or_404(User, id=student_id, role='student')
    
    # Verify supervisor has access to this student
    try:
        project = Project.objects.get(student=student, supervisor=request.user)
    except Project.DoesNotExist:
        messages.error(request, 'You do not supervise this student.')
        return redirect('analytics:supervisor_analytics')
    
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest_stress = StressLevel.objects.filter(
        student=student
    ).order_by('-calculated_at').first()
    
    # Get stress trend (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    stress_history = StressLevel.objects.filter(
        student=student,
        calculated_at__gte=thirty_days_ago
    ).order_by('calculated_at')
    
    # Performance metrics
    performance = PerformanceCalculator.calculate_student_performance(student)
    
    # FIXED: Use ProjectActivity instead of non-existent ProjectProgress
    progress_history = ProjectActivity.objects.filter(
        project=project
    ).order_by('-timestamp')[:10]
    
    # Log sheets
    log_sheets = ProjectLogSheet.objects.filter(
        project=project
    ).order_by('-week_number')[:5]
    
    # Meetings
    meetings = GroupMeeting.objects.filter(
        project=project
    ).order_by('-scheduled_date')[:5]
    
    context = {
        'title': f'Analytics - {student.display_name}',
        'student': student,
        'project': project,
        'latest_stress': latest_stress,
        'stress_history': stress_history,
        'performance': performance,
        'progress_history': progress_history,
        'log_sheets': log_sheets,
        'meetings': meetings,
    }
    
    return render(request, 'analytics/supervisor_student_profile.html', context)

# ========== ADDITIONAL FIXED FUNCTIONS ==========

@login_required
def get_stress_history(request, days=30):
    """Get stress history for the current user"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Students only'}, status=403)
    
    time_threshold = timezone.now() - timedelta(days=days)
    
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    recent_stress = StressLevel.objects.filter(
        student=request.user,
        calculated_at__gte=time_threshold
    ).order_by('-calculated_at')
    
    data = [{
        'timestamp': stress.calculated_at.isoformat(),
        'level': stress.level,
        'category': stress.stress_category
    } for stress in recent_stress]
    
    return JsonResponse({'stress_history': data})

@login_required
def get_latest_stress(request):
    """Get latest stress reading for the current user"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Students only'}, status=403)
    
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest = StressLevel.objects.filter(student=request.user).order_by('-calculated_at').first()
    
    if latest:
        return JsonResponse({
            'level': latest.level,
            'category': latest.stress_category,
            'timestamp': latest.calculated_at.isoformat(),
            'has_data': True
        })
    else:
        return JsonResponse({'has_data': False})

@login_required
def get_stress_trend(request):
    """Get stress trend data for charts"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Students only'}, status=403)
    
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    week_ago = timezone.now() - timedelta(days=7)
    
    stress_data = StressLevel.objects.filter(
        student=request.user,
        calculated_at__gte=week_ago
    ).order_by('calculated_at')
    
    dates = [stress.calculated_at.strftime('%Y-%m-%d') for stress in stress_data]
    levels = [stress.level for stress in stress_data]
    
    return JsonResponse({
        'dates': dates,
        'levels': levels,
        'count': len(dates)
    })

@login_required
def get_stress_summary(request):
    """Get stress summary for dashboard"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Students only'}, status=403)
    
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    latest = StressLevel.objects.filter(student=request.user).latest('calculated_at')
    
    month_ago = timezone.now() - timedelta(days=30)
    # FIXED: Use 'calculated_at' instead of 'timestamp'
    previous_month_stress = StressLevel.objects.filter(
        student=request.user,
        calculated_at__gte=month_ago,
        calculated_at__lte=latest.calculated_at - timedelta(days=30)
    ).order_by('calculated_at').first()
    
    context = {
        'current_stress': latest.level,
        'previous_stress': previous_month_stress.level if previous_month_stress else None,
        'trend': 'up' if previous_month_stress and latest.level > previous_month_stress.level else 'down',
        'category': latest.stress_category
    }
    
    return JsonResponse(context)