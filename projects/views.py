# File: projects/views.py - COMPLETE FIXED VERSION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from accounts.models import User
from .models import Project, ProjectDeliverable, ProjectActivity
from .forms import (
    ProjectForm, ProjectSubmitForm, ProjectReviewForm,
    ProjectDeliverableForm, DeliverableReviewForm
)
# CRITICAL IMPORTS FOR REAL STRESS ANALYSIS
from analytics.sentiment import AdvancedSentimentAnalyzer
from analytics.models import StressLevel
from analytics.calculators import PerformanceCalculator, ProgressCalculator

from .forms import LogSheetApprovalForm, MeetingScheduleForm, MeetingMinutesForm, ProgressNoteForm
from .models import ProjectLogSheet, SupervisorMeeting, StudentProgressNote
from analytics.calculators import PerformanceCalculator, StressCalculator

@login_required
def my_project(request):
    """Student's own project view with REAL stress analysis - FULLY FIXED"""
    
    if not request.user.is_student:
        messages.error(request, 'This page is for students only.')
        return redirect('dashboard:home')
    
    # Get student's project
    current_batch = timezone.now().year
    try:
        project = Project.objects.get(
            student=request.user,
            batch_year=current_batch
        )
    except Project.DoesNotExist:
        project = None
    
    # ===========================================================================
    # REAL STRESS ANALYSIS - NO MORE HARDCODED VALUES
    # ===========================================================================
    latest_stress = None
    stress_score = 0
    stress_level = 'low'
    stress_label = 'Low Stress'
    stress_factors = []
    high_stress = False
    
    if project:
        # Check if we have recent stress analysis (within last 24 hours)
        latest_stress = StressLevel.objects.filter(
            student=request.user
        ).order_by('-calculated_at').first()
        
        needs_new_analysis = (
            not latest_stress or 
            (timezone.now() - latest_stress.calculated_at).total_seconds() > 86400
        )
        
        if needs_new_analysis:
            try:
                print(f"[STRESS] Calculating new stress analysis for {request.user.display_name}")
                analyzer = AdvancedSentimentAnalyzer(request.user)
                latest_stress = analyzer.comprehensive_stress_analysis(days=7)
                
                if latest_stress:
                    print(f"[STRESS] Analysis successful: {latest_stress.level:.2f}%")
                else:
                    print(f"[STRESS] No meaningful data for analysis")
                    
            except Exception as e:
                print(f"[STRESS ERROR] {type(e).__name__}: {e}")
                latest_stress = None
        else:
            print(f"[STRESS] Using cached analysis from {latest_stress.calculated_at}")
        
        # Extract real stress data
        if latest_stress:
            stress_score = int(latest_stress.level)
            high_stress = stress_score >= 70
            
            # Determine stress level category
            if stress_score >= 70:
                stress_level = 'high'
                stress_label = 'High Stress - Need Support'
            elif stress_score >= 40:
                stress_level = 'medium'
                stress_label = 'Moderate Stress'
            else:
                stress_level = 'low'
                stress_label = 'Low Stress'
            
            # Build real stress factors breakdown
            stress_factors = [
                {
                    'name': 'Chat Sentiment',
                    'score': int(latest_stress.chat_sentiment_score),
                    'level': get_factor_level(latest_stress.chat_sentiment_score)
                },
                {
                    'name': 'Deadline Pressure',
                    'score': int(latest_stress.deadline_pressure),
                    'level': get_factor_level(latest_stress.deadline_pressure)
                },
                {
                    'name': 'Workload',
                    'score': int(latest_stress.workload_score),
                    'level': get_factor_level(latest_stress.workload_score)
                },
                {
                    'name': 'Social Isolation',
                    'score': int(latest_stress.social_isolation_score),
                    'level': get_factor_level(latest_stress.social_isolation_score)
                }
            ]
            
            print(f"[STRESS] Factors: {stress_factors}")
    
    # ===========================================================================
    # REAL PERFORMANCE CALCULATION
    # ===========================================================================
    performance_grade = 'N/A'
    performance_score = 0
    
    if project:
        try:
            performance = PerformanceCalculator.calculate_student_performance(request.user)
            performance_grade = performance['grade']
            performance_score = performance['overall_score']
            print(f"[PERFORMANCE] Grade: {performance_grade}, Score: {performance_score:.2f}")
        except Exception as e:
            print(f"[PERFORMANCE ERROR] {e}")
    
    # ===========================================================================
    # DELIVERABLES DATA
    # ===========================================================================
    completed_deliverables = 0
    total_deliverables = 5
    next_deliverable = None
    
    if project:
        completed_deliverables = project.deliverables.filter(is_approved=True).count()
        next_deliverable = project.deliverables.filter(
            is_approved=False
        ).order_by('stage').first()
    
    # ===========================================================================
    # RECENT ACTIVITIES
    # ===========================================================================
    recent_activities = []
    if project:
        recent_activities = project.activities.all().order_by('-timestamp')[:5]
    
    # ===========================================================================
    # AI RECOMMENDATIONS BASED ON REAL DATA
    # ===========================================================================
    ai_recommendations = []
    
    if project:
        # Progress-based recommendations
        if project.progress_percentage < 30:
            ai_recommendations.append({
                'priority': 'high',
                'icon': 'bx-error-circle',
                'title': 'Critical: Low Progress',
                'description': f'Your project is at {project.progress_percentage}% completion. Immediate action needed.',
                'action_url': None,
                'action_text': 'Review Timeline'
            })
        elif project.progress_percentage < 50:
            ai_recommendations.append({
                'priority': 'medium',
                'icon': 'bx-time',
                'title': 'Progress Behind Schedule',
                'description': 'Consider accelerating your work pace to meet deadlines.',
                'action_url': None,
                'action_text': 'View Tasks'
            })
        
        # Stress-based recommendations
        if stress_score >= 80:
            ai_recommendations.append({
                'priority': 'high',
                'icon': 'bx-heart',
                'title': 'Critical Stress Level',
                'description': 'Your stress is at critical levels. Please reach out for support immediately.',
                'action_url': f'/chat/supervisor/{project.supervisor.id}/' if project.supervisor else None,
                'action_text': 'Contact Supervisor'
            })
        elif stress_score >= 60:
            ai_recommendations.append({
                'priority': 'medium',
                'icon': 'bx-heart',
                'title': 'Elevated Stress Detected',
                'description': 'Take breaks and consider discussing workload with your supervisor.',
                'action_url': None,
                'action_text': 'View Wellness Tips'
            })
        
        # Deliverable-based recommendations
        if completed_deliverables < 2:
            ai_recommendations.append({
                'priority': 'medium',
                'icon': 'bx-file',
                'title': 'Submit More Deliverables',
                'description': 'Focus on completing deliverables to improve your progress.',
                'action_url': f'/projects/{project.pk}/submit/',
                'action_text': 'Submit Now'
            })
        
        # Performance-based recommendations
        if performance_score < 60:
            ai_recommendations.append({
                'priority': 'high',
                'icon': 'bx-trending-down',
                'title': 'Performance Needs Improvement',
                'description': 'Your performance metrics indicate need for improvement.',
                'action_url': f'/projects/{project.pk}/analytics/',
                'action_text': 'View Analytics'
            })
    
    # ===========================================================================
    # WELLNESS TIPS BASED ON REAL STRESS LEVEL
    # ===========================================================================
    wellness_tips = generate_wellness_tips(stress_score)
    
    # ===========================================================================
    # FINAL CONTEXT WITH REAL DATA
    # ===========================================================================
    context = {
        'title': 'My Project - PrimeTime',
        'project': project,
        'can_edit': project and project.status in ['draft', 'rejected'],
        'show_resubmit': project and project.status == 'rejected',
        'tab': request.GET.get('tab', 'overview'),
        
        # Student info
        'student_id': request.user.user_id,
        'department': request.user.department,
        'batch_year': request.user.batch_year,
        
        # REAL STRESS DATA
        'latest_stress': latest_stress,
        'stress_score': stress_score,
        'stress_level': stress_level,
        'stress_label': stress_label,
        'stress_factors': stress_factors,
        'high_stress': high_stress,
        
        # REAL PERFORMANCE DATA
        'performance_grade': performance_grade,
        'performance_score': performance_score,
        
        # REAL PROGRESS DATA
        'progress_percentage': project.progress_percentage if project else 0,
        'completed_deliverables': completed_deliverables,
        'total_deliverables': total_deliverables,
        'next_deliverable': next_deliverable,
        
        # DYNAMIC RECOMMENDATIONS
        'ai_recommendations': ai_recommendations,
        'recent_activities': recent_activities,
        'wellness_tips': wellness_tips,
        
        # Placeholder for future features
        'recommended_resources': [],
        'recommended_resources_count': 0,
        'group_members': [],
        'forum_discussions': [],
    }
    
    return render(request, 'projects/my_project.html', context)


# ===========================================================================
# HELPER FUNCTIONS FOR STRESS ANALYSIS
# ===========================================================================

def get_factor_level(score):
    """Convert stress factor score to Bootstrap color class"""
    if score >= 70:
        return 'danger'
    elif score >= 40:
        return 'warning'
    else:
        return 'success'


def generate_wellness_tips(stress_score):
    """Generate wellness tips based on actual stress level"""
    if stress_score >= 70:
        return [
            {'icon': 'bx-time-five', 'text': 'Take a 15-minute break every hour'},
            {'icon': 'bx-walk', 'text': 'Go for a walk to clear your mind'},
            {'icon': 'bx-moon', 'text': 'Prioritize 7-8 hours of sleep tonight'},
            {'icon': 'bx-conversation', 'text': 'Talk to your supervisor or counselor'},
            {'icon': 'bx-heart', 'text': 'Practice deep breathing exercises'}
        ]
    elif stress_score >= 40:
        return [
            {'icon': 'bx-timer', 'text': 'Use the Pomodoro technique (25 min focus, 5 min break)'},
            {'icon': 'bx-run', 'text': 'Include 20-30 minutes of physical activity'},
            {'icon': 'bx-water', 'text': 'Stay hydrated - drink water regularly'},
            {'icon': 'bx-calendar-check', 'text': 'Break tasks into smaller, manageable chunks'}
        ]
    else:
        return [
            {'icon': 'bx-check-circle', 'text': 'Great work! Keep maintaining your current pace'},
            {'icon': 'bx-time', 'text': 'Continue your healthy work-life balance'},
            {'icon': 'bx-happy', 'text': 'Stay connected with peers and mentors'},
            {'icon': 'bx-star', 'text': 'Share your success strategies with others'}
        ]


# ===========================================================================
# OTHER PROJECT VIEWS (KEEPING EXISTING FUNCTIONALITY)
# ===========================================================================

@login_required
def project_submit(request, pk):
    """Submit project for review (students only)"""
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student:
        return HttpResponseForbidden("You don't have permission to submit this project.")
    
    if project.status != 'draft':
        messages.error(request, 'Only draft projects can be submitted for review.')
        return redirect('projects:my_project')
    
    if request.method == 'POST':
        form = ProjectSubmitForm(request.POST)
        if form.is_valid():
            project.submit_for_review()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='submitted',
                details='Project submitted for admin review'
            )
            
            messages.success(request, 'Project submitted for review successfully!')
            return redirect('projects:my_project')
    else:
        form = ProjectSubmitForm()
    
    context = {
        'form': form,
        'project': project,
        'title': 'Submit Project for Review',
        'student_id': request.user.user_id,
        'department': request.user.department,
    }
    return render(request, 'projects/project_submit.html', context)


@login_required
def all_projects(request):
    """All projects view for admin and supervisors - UPDATED"""
    
    if not (request.user.is_supervisor or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    batch_filter = request.GET.get('batch', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    projects = Project.objects.all().select_related('student', 'supervisor', 'student__profile')
    
    if request.user.is_supervisor:
        projects = projects.filter(supervisor=request.user)
    
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(student__full_name__icontains=search_query) |
            Q(student__user_id__icontains=search_query) |
            Q(programming_languages__icontains=search_query)
        )
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    if batch_filter:
        projects = projects.filter(batch_year=batch_filter)
    
    sort_options = {
        'title': 'title',
        '-title': '-title',
        'progress': 'progress_percentage',
        '-progress': '-progress_percentage',
        'status': 'status',
        'created': 'created_at',
        '-created': '-created_at',
        'student': 'student__full_name'
    }
    
    if sort_by in sort_options:
        projects = projects.order_by(sort_options[sort_by])
    
    paginator = Paginator(projects, 20)
    page = request.GET.get('page')
    projects_page = paginator.get_page(page)
    
    # Count pending projects for badge
    pending_projects = 0
    if request.user.is_admin:
        pending_projects = Project.objects.filter(status='pending').count()
    
    context = {
        'title': 'All Projects - PrimeTime',
        'projects': projects_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'batch_filter': batch_filter,
        'sort_by': sort_by,
        'statuses': Project.STATUS_CHOICES,
        'batches': range(2079, 2090),
        'is_supervisor': request.user.is_supervisor,
        'is_admin': request.user.is_admin,
        'pending_projects': pending_projects,
    }
    
    return render(request, 'projects/all_projects.html', context)

@login_required
def project_create(request):
    """Create a new project (students only)"""
    
    if not request.user.is_student:
        messages.error(request, 'Only students can create projects.')
        return redirect('dashboard:home')
    
    current_batch = timezone.now().year
    existing_project = Project.objects.filter(
        student=request.user,
        batch_year=current_batch
    ).first()
    
    if existing_project:
        messages.info(request, 'You already have a project for this batch.')
        return redirect('projects:my_project')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = request.user
            project.batch_year = current_batch
            project.status = 'draft'
            project.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='created',
                details=f'Project "{project.title}" created'
            )
            
            messages.success(request, 'Project created successfully!')
            return redirect('projects:my_project')
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
        'title': 'Create Project - PrimeTime',
        'student_id': request.user.user_id,
        'department': request.user.department,
        'batch_year': request.user.batch_year,
    }
    return render(request, 'projects/project_form.html', context)

@login_required
def project_edit(request, pk):
    """Edit existing project with resubmit functionality"""
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student:
        return HttpResponseForbidden("You don't have permission to edit this project.")
    
    if not project.is_editable:
        messages.error(request, 'This project cannot be edited in its current status.')
        return redirect('projects:my_project')
    
    # Check if this is a resubmission after rejection
    is_resubmission = project.status == 'rejected'
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        # Check if user wants to resubmit immediately
        resubmit_now = request.POST.get('resubmit_now') == 'true'
        
        if form.is_valid():
            form.save()
            
            # If resubmitting, change status to pending
            if resubmit_now and is_resubmission:
                project.status = 'pending'
                project.submitted_at = timezone.now()
                project.rejection_reason = ''  # Clear rejection reason
                project.save()
                
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    action='submitted',
                    details='Project revised and resubmitted for review'
                )
                
                messages.success(request, 'Project updated and resubmitted for review successfully!')
            else:
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    action='updated',
                    details='Project details updated'
                )
                
                messages.success(request, 'Project updated successfully!')
            
            return redirect('projects:my_project')
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'is_resubmission': is_resubmission,
        'title': f'Edit Project - {project.title}',
        'student_id': request.user.user_id,
        'department': request.user.department,
    }
    return render(request, 'projects/project_form.html', context)

@login_required
def project_detail(request, pk):
    """View project details"""
    
    project = get_object_or_404(Project, pk=pk)
    
    can_edit = request.user == project.student and project.is_editable
    can_review = request.user.is_admin and project.status == 'pending'
    can_manage_deliverables = request.user == project.supervisor
    
    has_access = (
        request.user == project.student or
        request.user == project.supervisor or
        request.user.is_admin
    )
    
    if not has_access:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:all_projects')
    
    deliverables = project.deliverables.all().order_by('stage')
    activities = project.activities.all()[:10]
    
    context = {
        'project': project,
        'deliverables': deliverables,
        'activities': activities,
        'can_edit': can_edit,
        'can_review': can_review,
        'can_manage_deliverables': can_manage_deliverables,
        'title': project.title,
        'is_student': request.user.is_student,
        'is_supervisor': request.user.is_supervisor,
        'is_admin': request.user.is_admin,
        'student_id': project.student.user_id if project.student else None,
        'student_department': project.student.department if project.student else None,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_analytics(request, pk):
    """Project analytics dashboard"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student and not request.user.is_admin and request.user != project.supervisor:
        messages.error(request, 'You do not have permission to view these analytics.')
        return redirect('projects:my_project')
    
    deliverables = project.deliverables.all()
    completed_deliverables = deliverables.filter(is_approved=True).count()
    total_deliverables = 5
    
    approved_deliverables = deliverables.filter(is_approved=True, marks__isnull=False)
    if approved_deliverables.exists():
        average_marks = sum(d.marks for d in approved_deliverables) / approved_deliverables.count()
    else:
        average_marks = 0
    
    context = {
        'project': project,
        'title': f'Analytics - {project.title}',
        'progress_percentage': project.progress_percentage,
        'completed_deliverables': completed_deliverables,
        'total_deliverables': total_deliverables,
        'completion_rate': int((completed_deliverables / total_deliverables) * 100) if total_deliverables > 0 else 0,
        'average_marks': average_marks,
        'days_remaining': 30,
        'progress_timeline_labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Current'],
        'progress_timeline_data': [10, 25, 45, 70, project.progress_percentage],
        'expected_progress_data': [20, 40, 60, 80, 100],
        'deliverable_progress': min(100, int((completed_deliverables / total_deliverables) * 100)),
        'marks_progress': min(100, int(average_marks)),
        'activity_progress': min(100, project.progress_percentage),
        'deliverable_labels': ['Proposal', 'Mid Defense', 'Pre Defense', 'Final Defense', 'Documentation'],
        'deliverable_marks': [85, 78, 92, 0, 0],
        'activity_heatmap_data': [],
        'performance_insights': [
            {
                'type': 'success',
                'icon': 'bx-trending-up',
                'title': 'Good Progress',
                'description': 'You are maintaining steady progress on your project.'
            }
        ],
        'recommendations': [
            {
                'priority': 'medium',
                'priority_label': 'Medium',
                'title': 'Focus on Final Deliverables',
                'description': 'Consider starting work on your final defense materials.',
                'action_url': '#',
                'action_label': 'View Resources'
            }
        ]
    }
    
    return render(request, 'projects/project_analytics.html', context)

# ADD THESE NEW VIEWS TO projects/views.py


@login_required
def project_wellness(request, pk):
    """Project wellness and stress analysis page"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student:
        messages.error(request, 'Access denied.')
        return redirect('projects:my_project')
    
    # Get real stress data
    from analytics.models import StressLevel
    latest_stress = StressLevel.objects.filter(
        student=request.user
    ).order_by('-calculated_at').first()
    
    stress_score = int(latest_stress.level) if latest_stress else 0
    stress_level = 'low'
    if stress_score >= 70:
        stress_level = 'high'
    elif stress_score >= 40:
        stress_level = 'medium'
    
    stress_factors = []
    if latest_stress:
        stress_factors = [
            {
                'name': 'Chat Sentiment',
                'score': int(latest_stress.chat_sentiment_score),
                'level': get_factor_level(latest_stress.chat_sentiment_score)
            },
            {
                'name': 'Deadline Pressure',
                'score': int(latest_stress.deadline_pressure),
                'level': get_factor_level(latest_stress.deadline_pressure)
            },
            {
                'name': 'Workload',
                'score': int(latest_stress.workload_score),
                'level': get_factor_level(latest_stress.workload_score)
            },
            {
                'name': 'Social Isolation',
                'score': int(latest_stress.social_isolation_score),
                'level': get_factor_level(latest_stress.social_isolation_score)
            }
        ]
    
    wellness_tips = generate_wellness_tips(stress_score)
    
    context = {
        'project': project,
        'title': f'Wellness - {project.title}',
        'stress_score': stress_score,
        'stress_level': stress_level,
        'stress_factors': stress_factors,
        'wellness_tips': wellness_tips,
        'latest_stress': latest_stress,
        'high_stress': stress_score >= 70,
    }
    
    return render(request, 'projects/project_wellness.html', context)


@login_required
def stress_analysis(request, pk):
    """Detailed stress analysis (redirects to wellness)"""
    return redirect('projects:project_wellness', pk=pk)


@login_required
def project_team(request, pk):
    """Project team and collaboration page"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student and request.user != project.supervisor and not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('projects:my_project')
    
    # Get group members
    from groups.models import GroupMembership
    try:
        group_membership = GroupMembership.objects.get(
            student=project.student,
            is_active=True
        )
        group = group_membership.group
        group_members = User.objects.filter(
            group_memberships__group=group,
            group_memberships__is_active=True
        ).exclude(id=project.student.id)
    except GroupMembership.DoesNotExist:
        group = None
        group_members = []
    
    # Get recent activities
    recent_activities = project.activities.all().order_by('-timestamp')[:10]
    
    context = {
        'project': project,
        'title': f'Team - {project.title}',
        'group': group,
        'group_members': group_members,
        'recent_activities': recent_activities,
        'supervisor': project.supervisor,
    }
    
    return render(request, 'projects/project_team.html', context)


@login_required  
def project_collaboration(request, pk):
    """Project collaboration (redirects to team)"""
    return redirect('projects:project_team', pk=pk)

@login_required
def project_recommendations(request, pk):
    """AI-powered project recommendations"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student:
        messages.error(request, 'Access denied.')
        return redirect('projects:my_project')
    
    context = {
        'project': project,
        'title': f'Recommendations - {project.title}',
        'total_recommendations': 0,
        'match_score': 85,
        'trending_count': 0,
        'high_rated_count': 0,
        'categories': [],
        'tech_recommendations': [],
        'collaborative_recommendations': [],
        'trending_recommendations': []
    }
    
    return render(request, 'projects/project_recommendations.html', context)


@login_required
def deliverable_submit(request, pk):
    """Submit project deliverable"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.user != project.student:
        messages.error(request, 'Only the project student can submit deliverables.')
        return redirect('projects:my_project')
    
    messages.info(request, 'Deliverable submission feature will be implemented soon.')
    return redirect('projects:my_project')

@login_required
def assign_supervisor_page(request, pk):
    """
    Supervisor assignment page with detailed view
    Shows all supervisors with their workload
    """
    if not request.user.is_admin:
        messages.error(request, 'Only admins can assign supervisors.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    if project.status != 'approved':
        messages.error(request, 'Only approved projects can have supervisors assigned.')
        return redirect('projects:all_projects')
    
    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor_id')
        
        if not supervisor_id:
            messages.error(request, 'Please select a supervisor.')
            return redirect('projects:assign_supervisor_page', pk=pk)
        
        try:
            supervisor = User.objects.get(id=supervisor_id, role='supervisor')
            
            # Assign supervisor
            project.supervisor = supervisor
            if project.status == 'approved':
                project.status = 'in_progress'
            project.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='supervisor_assigned',
                details=f'Supervisor {supervisor.display_name} assigned to project'
            )
            
            messages.success(
                request, 
                f'Supervisor {supervisor.display_name} successfully assigned to {project.title}!'
            )
            return redirect('projects:all_projects')
            
        except User.DoesNotExist:
            messages.error(request, 'Invalid supervisor selected.')
            return redirect('projects:assign_supervisor_page', pk=pk)
    
    # Get all supervisors with their workload
    supervisors = User.objects.filter(role='supervisor').annotate(
        supervised_count=Count('supervised_projects')
    ).order_by('supervised_count', 'full_name')
    
    # Calculate availability for each supervisor
    supervisor_data = []
    for supervisor in supervisors:
        supervised_count = supervisor.supervised_count
        workload_percentage = min(int((supervised_count / 7) * 100), 100)
        is_available = supervised_count < 7
        
        # Get current students
        current_students = User.objects.filter(
            projects__supervisor=supervisor,
            projects__status__in=['in_progress', 'approved']
        ).distinct()
        
        supervisor_data.append({
            'id': supervisor.id,
            'display_name': supervisor.display_name,
            'email': supervisor.email,
            'department': supervisor.department,
            'profile': supervisor.profile,
            'supervised_count': supervised_count,
            'workload_percentage': workload_percentage,
            'is_available': is_available,
            'current_students': current_students
        })
    
    context = {
        'project': project,
        'supervisors': supervisor_data,
        'title': f'Assign Supervisor - {project.title}',
    }
    
    return render(request, 'projects/assign_supervisor.html', context)

@login_required
def project_review(request, pk):
    """Review project (admin only)"""
    
    if not request.user.is_admin:
        messages.error(request, 'Only admins can review projects.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    if project.status != 'pending':
        messages.error(request, 'This project is not pending review.')
        return redirect('projects:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        form = ProjectReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'approve':
                project.approve(request.user)
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    action='approved',
                    details='Project approved by admin'
                )
                messages.success(request, f'Project "{project.title}" has been approved.')
            else:
                reason = form.cleaned_data['rejection_reason']
                project.reject(request.user, reason)
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    action='rejected',
                    details=f'Project rejected: {reason}'
                )
                messages.warning(request, f'Project "{project.title}" has been rejected.')
            
            return redirect('dashboard:admin_dashboard')
    else:
        form = ProjectReviewForm()
    
    context = {
        'form': form,
        'project': project,
        'title': f'Review Project: {project.title}',
        'student_id': project.student.user_id if project.student else None,
        'student_department': project.student.department if project.student else None,
    }
    return render(request, 'projects/project_review.html', context)


@login_required
def project_list(request):
    """List all projects with filters"""
    
    status_filter = request.GET.get('status', '')
    batch_filter = request.GET.get('batch', '')
    search_query = request.GET.get('q', '')
    
    projects = Project.objects.all().select_related('student', 'supervisor')
    
    if request.user.is_student:
        projects = projects.filter(student=request.user)
    elif request.user.is_supervisor:
        projects = projects.filter(supervisor=request.user)
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    if batch_filter:
        projects = projects.filter(batch_year=batch_filter)
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(programming_languages__icontains=search_query) |
            Q(student__full_name__icontains=search_query) |
            Q(student__user_id__icontains=search_query)
        )
    
    paginator = Paginator(projects, 15)
    page = request.GET.get('page')
    projects_page = paginator.get_page(page)
    
    context = {
        'projects': projects_page,
        'status_filter': status_filter,
        'batch_filter': batch_filter,
        'search_query': search_query,
        'statuses': Project.STATUS_CHOICES,
        'batches': range(2079, 2090),
        'title': 'Projects - PrimeTime',
        'is_student': request.user.is_student,
        'is_supervisor': request.user.is_supervisor,
        'is_admin': request.user.is_admin,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_assign_supervisor(request, pk):
    """Assign supervisor to project (admin only)"""
    
    if not request.user.is_admin:
        messages.error(request, 'Only admins can assign supervisors.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor_id')
        try:
            supervisor = User.objects.get(id=supervisor_id, role='supervisor')
            project.supervisor = supervisor
            project.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='supervisor_assigned',
                details=f'Supervisor {supervisor.full_name} assigned to project'
            )
            
            messages.success(request, f'Supervisor {supervisor.full_name} assigned successfully!')
        except User.DoesNotExist:
            messages.error(request, 'Invalid supervisor selected.')
    
    return redirect('projects:project_detail', pk=project.pk)


@login_required
def supervisor_projects(request):
    """Supervisor's projects dashboard"""
    
    if not request.user.is_supervisor:
        messages.error(request, 'Access denied. Supervisors only.')
        return redirect('dashboard:home')
    
    projects = Project.objects.filter(supervisor=request.user).select_related('student')
    
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(student__full_name__icontains=search_query) |
            Q(student__user_id__icontains=search_query)
        )
    
    context = {
        'projects': projects,
        'status_filter': status_filter,
        'search_query': search_query,
        'statuses': Project.STATUS_CHOICES,
        'title': 'My Supervised Projects - PrimeTime',
        'department': request.user.department,
    }
    
    return render(request, 'projects/supervisor_projects.html', context)

# ===========================================================================
# NEW SUPERVISOR MANAGEMENT VIEWS
# ===========================================================================

@login_required
def supervisor_project_detail(request, pk):
    """
    Comprehensive supervisor view of project with:
    - Student info & analytics
    - Log sheets
    - Meetings
    - Stress monitoring
    - Deliverables tracking
    - Private notes
    """
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can access this page.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    # Verify supervisor is assigned to this project
    if project.supervisor != request.user:
        messages.error(request, 'You are not the supervisor for this project.')
        return redirect('projects:supervisor_projects')
    
    student = project.student
    
    # ==================================================================
    # STUDENT ANALYTICS & PERFORMANCE
    # ==================================================================
    
    # Get latest stress level
    latest_stress = StressLevel.objects.filter(
        student=student
    ).order_by('-calculated_at').first()
    
    # Get stress trend
    stress_trend = None
    if latest_stress:
        stress_trend = StressCalculator.get_stress_trend(student, days=30)
    
    # Calculate performance
    performance = PerformanceCalculator.calculate_student_performance(student)
    
    # ==================================================================
    # LOG SHEETS
    # ==================================================================
    
    log_sheets = ProjectLogSheet.objects.filter(
        project=project
    ).order_by('-week_number')
    
    pending_log_sheets = log_sheets.filter(is_approved=False)
    approved_log_sheets = log_sheets.filter(is_approved=True)
    
    # ==================================================================
    # MEETINGS
    # ==================================================================
    
    upcoming_meetings = SupervisorMeeting.objects.filter(
        project=project,
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    ).order_by('scheduled_date')
    
    past_meetings = SupervisorMeeting.objects.filter(
        project=project,
        status='completed'
    ).order_by('-scheduled_date')[:10]
    
    # ==================================================================
    # DELIVERABLES
    # ==================================================================
    
    deliverables = project.deliverables.all().order_by('stage')
    completed_deliverables = deliverables.filter(is_approved=True).count()
    total_deliverables = deliverables.count()
    
    # ==================================================================
    # SUPERVISOR NOTES
    # ==================================================================
    
    supervisor_notes = StudentProgressNote.objects.filter(
        project=project,
        supervisor=request.user
    ).order_by('-created_at')[:20]
    
    # ==================================================================
    # RECENT ACTIVITIES
    # ==================================================================
    
    recent_activities = project.activities.all().order_by('-timestamp')[:15]
    
    # ==================================================================
    # STATISTICS
    # ==================================================================
    
    total_hours_logged = log_sheets.aggregate(
        total=Sum('hours_spent')
    )['total'] or 0
    
    average_rating = log_sheets.filter(
        supervisor_rating__isnull=False
    ).aggregate(
        avg=Avg('supervisor_rating')
    )['avg']
    
    meeting_attendance_rate = 0
    if past_meetings.exists():
        attended = past_meetings.filter(student_attended=True).count()
        meeting_attendance_rate = int((attended / past_meetings.count()) * 100)
    
    context = {
        'title': f'Supervise: {project.title}',
        'project': project,
        'student': student,
        
        # Analytics
        'latest_stress': latest_stress,
        'stress_trend': stress_trend,
        'performance': performance,
        
        # Log sheets
        'log_sheets': log_sheets,
        'pending_log_sheets': pending_log_sheets,
        'approved_log_sheets': approved_log_sheets,
        
        # Meetings
        'upcoming_meetings': upcoming_meetings,
        'past_meetings': past_meetings,
        
        # Deliverables
        'deliverables': deliverables,
        'completed_deliverables': completed_deliverables,
        'total_deliverables': total_deliverables,
        
        # Notes
        'supervisor_notes': supervisor_notes,
        
        # Activities
        'recent_activities': recent_activities,
        
        # Statistics
        'total_hours_logged': total_hours_logged,
        'average_rating': average_rating,
        'meeting_attendance_rate': meeting_attendance_rate,
        
        # Tab management
        'active_tab': request.GET.get('tab', 'overview'),
    }
    
    return render(request, 'projects/supervisor_project_detail.html', context)


@login_required
def approve_log_sheet(request, pk):
    """Approve and provide feedback on student log sheet"""
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can approve log sheets.')
        return redirect('dashboard:home')
    
    log_sheet = get_object_or_404(ProjectLogSheet, pk=pk)
    project = log_sheet.project
    
    # Verify supervisor
    if project.supervisor != request.user:
        messages.error(request, 'You are not the supervisor for this project.')
        return redirect('projects:supervisor_projects')
    
    if request.method == 'POST':
        form = LogSheetApprovalForm(request.POST, instance=log_sheet)
        if form.is_valid():
            log_sheet = form.save(commit=False)
            log_sheet.is_approved = True
            log_sheet.supervisor_signature = request.user.display_name
            log_sheet.reviewed_at = timezone.now()
            log_sheet.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='logsheet_approved',
                details=f'Week {log_sheet.week_number} log sheet approved with rating {log_sheet.supervisor_rating}/5'
            )
            
            messages.success(
                request,
                f'Log sheet for Week {log_sheet.week_number} approved successfully!'
            )
            return redirect('projects:supervisor_project_detail', pk=project.pk)
    else:
        form = LogSheetApprovalForm(instance=log_sheet)
    
    context = {
        'form': form,
        'log_sheet': log_sheet,
        'project': project,
        'title': f'Approve Log Sheet - Week {log_sheet.week_number}',
    }
    return render(request, 'projects/approve_log_sheet.html', context)


@login_required
def schedule_meeting(request, pk):
    """Schedule a meeting with student"""
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can schedule meetings.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    # Verify supervisor
    if project.supervisor != request.user:
        messages.error(request, 'You are not the supervisor for this project.')
        return redirect('projects:supervisor_projects')
    
    if request.method == 'POST':
        form = MeetingScheduleForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.project = project
            meeting.status = 'scheduled'
            meeting.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='meeting_scheduled',
                details=f'{meeting.get_meeting_type_display()} scheduled for {meeting.scheduled_date.strftime("%b %d, %Y at %I:%M %p")}'
            )
            
            messages.success(
                request,
                f'Meeting scheduled successfully for {meeting.scheduled_date.strftime("%b %d, %Y at %I:%M %p")}'
            )
            return redirect('projects:supervisor_project_detail', pk=project.pk)
    else:
        form = MeetingScheduleForm()
    
    context = {
        'form': form,
        'project': project,
        'student': project.student,
        'title': f'Schedule Meeting - {project.title}',
    }
    return render(request, 'projects/schedule_meeting.html', context)


@login_required
def record_meeting_minutes(request, meeting_id):
    """Record meeting minutes after meeting"""
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can record meeting minutes.')
        return redirect('dashboard:home')
    
    meeting = get_object_or_404(SupervisorMeeting, pk=meeting_id)
    project = meeting.project
    
    # Verify supervisor
    if project.supervisor != request.user:
        messages.error(request, 'You are not the supervisor for this project.')
        return redirect('projects:supervisor_projects')
    
    if request.method == 'POST':
        form = MeetingMinutesForm(request.POST, instance=meeting)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.status = 'completed'
            meeting.completed_at = timezone.now()
            meeting.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='meeting_completed',
                details=f'{meeting.get_meeting_type_display()} completed - Attendance: {"Present" if meeting.student_attended else "Absent"}'
            )
            
            messages.success(request, 'Meeting minutes recorded successfully!')
            return redirect('projects:supervisor_project_detail', pk=project.pk)
    else:
        form = MeetingMinutesForm(instance=meeting)
    
    context = {
        'form': form,
        'meeting': meeting,
        'project': project,
        'title': f'Record Minutes - {meeting.get_meeting_type_display()}',
    }
    return render(request, 'projects/record_meeting_minutes.html', context)


@login_required
def add_progress_note(request, pk):
    """Add a progress note for student"""
    if not request.user.is_supervisor:
        messages.error(request, 'Only supervisors can add progress notes.')
        return redirect('dashboard:home')
    
    project = get_object_or_404(Project, pk=pk)
    
    # Verify supervisor
    if project.supervisor != request.user:
        messages.error(request, 'You are not the supervisor for this project.')
        return redirect('projects:supervisor_projects')
    
    if request.method == 'POST':
        form = ProgressNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.project = project
            note.supervisor = request.user
            note.save()
            
            visibility = "visible to student" if note.is_visible_to_student else "private"
            messages.success(request, f'Progress note added successfully ({visibility})!')
            return redirect('projects:supervisor_project_detail', pk=project.pk)
    else:
        form = ProgressNoteForm()
    
    context = {
        'form': form,
        'project': project,
        'student': project.student,
        'title': f'Add Progress Note - {project.student.display_name}',
    }
    return render(request, 'projects/add_progress_note.html', context)