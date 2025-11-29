# File: analytics/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg
from django.utils import timezone

from .models import StressLevel, ProgressTracking, SupervisorFeedback, SupervisorMeetingLog
from .sentiment import AdvancedSentimentAnalyzer
from .calculators import StressCalculator, ProgressCalculator, PerformanceCalculator, AnalyticsDashboard
from .forms import SupervisorFeedbackForm
from accounts.models import User
from projects.models import Project


@login_required
def my_analytics(request):
    """Student view of their own analytics - ONLY REAL DATA"""
    if request.user.role != 'student':
        messages.error(request, "This page is for students only")
        return redirect('dashboard:home')

    # Get ONLY existing stress data - no defaults
    latest_stress = StressLevel.objects.filter(student=request.user).order_by('-calculated_at').first()
    
    # Only calculate trends if we have actual data
    stress_trend = None
    stress_history = None
    if latest_stress:
        stress_trend = StressCalculator.get_stress_trend(request.user, days=30)
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

    context = {
        'analytics': analytics,
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
        from groups.models import GroupMembership
        is_supervisor = GroupMembership.objects.filter(
            student=student,
            group__supervisor=request.user,
            is_active=True
        ).exists()

        if not is_supervisor:
            messages.error(request, "You are not the supervisor for this student")
            return redirect('analytics:supervisor_analytics')

    # Get comprehensive stress data - only if exists
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()
    stress_trend = None
    stress_history = None
    
    if latest_stress:
        stress_trend = StressCalculator.get_stress_trend(student, days=60)
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

        return JsonResponse({
            'success': True,
            'stress_level': stress_record.level,
            'category': stress_record.stress_category,
            'message': f'Your current stress level is {stress_record.level:.1f}% ({stress_record.stress_category})'
        })
    except Exception as e:
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
    from groups.models import GroupMembership
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

    # Get latest stress level - only if exists
    latest_stress = StressLevel.objects.filter(student=student).order_by('-calculated_at').first()

    # Get stress trend (last 30 days) - only if stress data exists
    stress_history = None
    if latest_stress:
        stress_history = StressLevel.objects.filter(student=student).order_by('-calculated_at')[:30]

    # Get latest progress - only if project exists
    latest_progress = None
    if project:
        latest_progress = ProgressTracking.objects.filter(project=project).order_by('-calculated_at').first()

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
    from groups.models import GroupMembership
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
    
    from .sentiment import AdvancedSentimentAnalyzer
    from chat.models import Message  # Add this import
    
    analyzer = AdvancedSentimentAnalyzer(request.user)
    
    # Check what data exists - FIXED THIS LINE
    has_chat_data = Message.objects.filter(user=request.user).exists()
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

    # Get high stress students (stress level > 70) - only if stress data exists
    high_stress_students = StressLevel.objects.filter(
        level__gte=70
    ).select_related('student').order_by('-level', '-timestamp')[:50]

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

