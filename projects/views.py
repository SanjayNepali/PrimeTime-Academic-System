# File: Desktop/Prime/projects/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import Project, ProjectDeliverable, ProjectActivity
from .forms import ProjectForm, ProjectDeliverableForm
from analytics.models import StressLevel
from analytics.sentiment import AdvancedSentimentAnalyzer


@login_required
def my_project(request):
    """Enhanced project view with stress analysis"""
    
    # Get user's project
    project = Project.objects.filter(student=request.user).first()
    
    if not project:
        # No project state
        context = {
            'project': None,
            'title': 'My Project - PrimeTime'
        }
        return render(request, 'projects/my_project.html', context)
    
    # Calculate progress
    total_deliverables = project.deliverables.count()
    completed_deliverables = project.deliverables.filter(is_approved=True).count()
    progress_percentage = 0
    if total_deliverables > 0:
        progress_percentage = (completed_deliverables / total_deliverables) * 100
    
    # Get next deliverable
    next_deliverable = project.deliverables.filter(is_approved=False).first()
    
    # Get recent activities
    recent_activities = ProjectActivity.objects.filter(
        project=project
    ).order_by('-timestamp')[:10]
    
    # STRESS ANALYSIS - Enhanced with fallbacks
    stress_level = "low"
    stress_score = 0
    stress_label = "No Data"
    high_stress = False
    
    try:
        analyzer = AdvancedSentimentAnalyzer(request.user)
        stress_analysis = analyzer.comprehensive_stress_analysis(days=7)
        
        if stress_analysis:
            stress_score = stress_analysis.level
            
            # Determine stress level and label
            if stress_score >= 70:
                stress_level = "high"
                stress_label = "High Stress"
                high_stress = True
            elif stress_score >= 40:
                stress_level = "medium"
                stress_label = "Medium Stress"
            else:
                stress_level = "low" 
                stress_label = "Low Stress"
        else:
            # Fallback: Calculate basic stress from project data
            stress_score = calculate_fallback_stress(project, completed_deliverables, total_deliverables)
            
            if stress_score >= 70:
                stress_level = "high"
                stress_label = "High Stress"
                high_stress = True
            elif stress_score >= 40:
                stress_level = "medium"
                stress_label = "Medium Stress"
            else:
                stress_level = "low"
                stress_label = "Low Stress"
                
    except Exception as e:
        print(f"Stress analysis error: {e}")
        # Final fallback
        stress_score = 35  # Default neutral
        stress_level = "low"
        stress_label = "Analysis Failed"
    
    # Performance calculation
    performance_score = calculate_performance_score(project, completed_deliverables, total_deliverables)
    performance_grade = calculate_grade(performance_score)
    
    # AI recommendations
    ai_recommendations = generate_ai_recommendations(
        project, 
        progress_percentage, 
        stress_score, 
        completed_deliverables,
        total_deliverables
    )
    
    # Stress factors for detailed analysis
    stress_factors = [
        {'name': 'Project Progress', 'score': max(0, 100 - progress_percentage), 'level': 'warning'},
        {'name': 'Deadline Pressure', 'score': min(100, (total_deliverables - completed_deliverables) * 20), 'level': 'info'},
        {'name': 'Workload', 'score': min(100, total_deliverables * 15), 'level': 'success'},
    ]
    
    # Wellness tips based on stress level
    wellness_tips = generate_wellness_tips(stress_level)
    
    context = {
        'project': project,
        'progress_percentage': progress_percentage,
        'completed_deliverables': completed_deliverables,
        'total_deliverables': total_deliverables,
        'next_deliverable': next_deliverable,
        'recent_activities': recent_activities,
        'stress_level': stress_level,
        'stress_score': stress_score,
        'stress_label': stress_label,
        'high_stress': high_stress,
        'stress_factors': stress_factors,
        'performance_score': performance_score,
        'performance_grade': performance_grade,
        'ai_recommendations': ai_recommendations,
        'wellness_tips': wellness_tips,
        'can_edit': request.user == project.student or request.user.is_admin,
        'title': f'{project.title} - PrimeTime'
    }
    
    return render(request, 'projects/my_project.html', context)


def calculate_fallback_stress(project, completed, total):
    """Calculate fallback stress when sentiment analysis fails"""
    if total == 0:
        return 25  # Low stress for new project
    
    progress = (completed / total) * 100
    
    # Base stress from progress
    base_stress = max(0, 50 - progress)
    
    # Stress from pending deliverables
    pending_stress = (total - completed) * 10
    
    # Time-based stress (projects older than 30 days)
    days_since_start = (timezone.now() - project.created_at).days
    time_stress = min(30, days_since_start * 0.5)
    
    total_stress = base_stress + pending_stress + time_stress
    return min(100, total_stress)


def calculate_performance_score(project, completed, total):
    """Calculate performance score"""
    if total == 0:
        return 85.0  # Default good score for new projects
    
    # Base score from completion rate
    completion_score = (completed / total) * 60
    
    # Activity bonus (recent activity)
    recent_activity = ProjectActivity.objects.filter(
        project=project,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).exists()
    activity_bonus = 20 if recent_activity else 0
    
    # Consistency bonus (steady progress)
    total_activities = ProjectActivity.objects.filter(project=project).count()
    consistency_bonus = min(20, total_activities * 2)
    
    return completion_score + activity_bonus + consistency_bonus


def calculate_grade(score):
    """Convert score to letter grade"""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'


def generate_ai_recommendations(project, progress, stress, completed, total):
    """Generate AI-powered recommendations"""
    recommendations = []
    
    # Progress-based recommendations
    if progress < 30:
        recommendations.append({
            'title': 'Start Strong',
            'description': 'Begin with foundational tasks to build momentum.',
            'priority': 'high',
            'icon': 'bx-rocket',
            'action_url': f'/projects/{project.pk}/deliverables/submit/',
            'action_text': 'Submit First Deliverable'
        })
    elif progress < 70:
        recommendations.append({
            'title': 'Maintain Momentum',
            'description': 'You\'re making good progress. Keep up the consistent work.',
            'priority': 'medium',
            'icon': 'bx-trending-up',
            'action_url': f'/projects/{project.pk}/',
            'action_text': 'View Progress'
        })
    
    # Stress-based recommendations
    if stress > 70:
        recommendations.append({
            'title': 'Manage Stress',
            'description': 'Your stress levels are high. Consider taking breaks and discussing challenges.',
            'priority': 'high',
            'icon': 'bx-heart',
            'action_url': '/chat/',
            'action_text': 'Chat with Supervisor'
        })
    elif stress > 40:
        recommendations.append({
            'title': 'Stay Balanced',
            'description': 'Monitor your workload and take regular breaks.',
            'priority': 'medium',
            'icon': 'bx-balance',
            'action_url': '#',
            'action_text': 'View Wellness Tips'
        })
    
    # Deliverable-based recommendations
    if total - completed > 2:
        recommendations.append({
            'title': 'Upcoming Deadlines',
            'description': f'You have {total - completed} deliverables pending. Plan your time effectively.',
            'priority': 'medium',
            'icon': 'bx-calendar',
            'action_url': f'/projects/{project.pk}/deliverables/',
            'action_text': 'View Deliverables'
        })
    
    return recommendations


def generate_wellness_tips(stress_level):
    """Generate wellness tips based on stress level"""
    base_tips = [
        {'icon': 'bx-time', 'text': 'Take regular breaks every 45-60 minutes'},
        {'icon': 'bx-water', 'text': 'Stay hydrated throughout the day'},
        {'icon': 'bx-walk', 'text': 'Incorporate short walks into your routine'},
    ]
    
    if stress_level == "high":
        base_tips.extend([
            {'icon': 'bx-brain', 'text': 'Practice deep breathing exercises'},
            {'icon': 'bx-conversation', 'text': 'Discuss challenges with your supervisor'},
            {'icon': 'bx-task', 'text': 'Break large tasks into smaller steps'},
        ])
    elif stress_level == "medium":
        base_tips.extend([
            {'icon': 'bx-music', 'text': 'Listen to calming music while working'},
            {'icon': 'bx-sun', 'text': 'Get some natural sunlight daily'},
        ])
    
    return base_tips


@login_required
def project_analytics(request, pk):
    """Project analytics dashboard"""
    project = get_object_or_404(Project, pk=pk, student=request.user)
    
    # Analytics data would go here
    context = {
        'project': project,
        'title': f'Analytics - {project.title}'
    }
    
    return render(request, 'projects/project_analytics.html', context)


@login_required 
def deliverable_submit(request, pk):
    """Submit a project deliverable"""
    project = get_object_or_404(Project, pk=pk, student=request.user)
    
    if request.method == 'POST':
        form = ProjectDeliverableForm(request.POST, request.FILES)
        if form.is_valid():
            deliverable = form.save(commit=False)
            deliverable.project = project
            deliverable.submitted_at = timezone.now()
            deliverable.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                action='deliverable_submitted',
                details=f'Submitted deliverable: {deliverable.stage}'
            )
            
            messages.success(request, 'Deliverable submitted successfully!')
            return redirect('projects:my_project')
    else:
        form = ProjectDeliverableForm()
    
    context = {
        'project': project,
        'form': form,
        'title': 'Submit Deliverable'
    }
    
    return render(request, 'projects/deliverable_submit.html', context)


# Other project management views...
@login_required
def project_create(request):
    """Create a new project"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = request.user
            project.batch_year = timezone.now().year
            project.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='created',
                details='Project created'
            )
            
            messages.success(request, 'Project created successfully!')
            return redirect('projects:my_project')
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
        'title': 'Create Project'
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_edit(request, pk):
    """Edit an existing project"""
    project = get_object_or_404(Project, pk=pk, student=request.user)
    
    if not project.is_editable:
        messages.error(request, 'This project cannot be edited in its current state.')
        return redirect('projects:my_project')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            
            # Log activity
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
        'title': 'Edit Project'
    }
    return render(request, 'projects/project_form.html', context)