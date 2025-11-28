# File: Desktop/Prime/projects/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from accounts.models import User
from .models import Project, ProjectDeliverable, ProjectActivity
from .forms import (
    ProjectForm, ProjectSubmitForm, ProjectReviewForm,
    ProjectDeliverableForm, DeliverableReviewForm
)


@login_required
def my_project(request):
    """Student's own project view with resources, forum, and help"""
    
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
    
    # Add required context for the enhanced template
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
        
        # Enhanced dashboard data (placeholders)
        'progress_percentage': project.progress_percentage if project else 0,
        'completed_deliverables': project.deliverables.filter(is_approved=True).count() if project else 0,
        'total_deliverables': 5,  # Total possible deliverables
        'stress_score': 35,
        'stress_level': 'low',
        'stress_label': 'Low Stress',
        'performance_grade': 'A',
        'performance_score': 88.5,
        'ai_recommendations': [],
        'recent_activities': project.activities.all()[:5] if project else [],
        'recommended_resources': [],
        'recommended_resources_count': 0,
        'group_members': [],
        'forum_discussions': [],
    }
    
    return render(request, 'projects/my_project.html', context)


@login_required
def all_projects(request):
    """All projects view for admin and supervisors - UPDATED"""
    
    if not (request.user.is_supervisor or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    batch_filter = request.GET.get('batch', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Build query
    projects = Project.objects.all().select_related('student', 'supervisor')
    
    # For supervisors, show only their supervised projects
    if request.user.is_supervisor:
        projects = projects.filter(supervisor=request.user)
    
    # Apply filters
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
    
    # Apply sorting
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
    
    # Pagination
    paginator = Paginator(projects, 20)
    page = request.GET.get('page')
    projects_page = paginator.get_page(page)
    
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
    }
    
    return render(request, 'projects/all_projects.html', context)


@login_required
def project_create(request):
    """Create a new project (students only) - UPDATED"""
    
    if not request.user.is_student:
        messages.error(request, 'Only students can create projects.')
        return redirect('dashboard:home')
    
    # Check if student already has a project for current batch
    current_batch = timezone.now().year
    existing_project = Project.objects.filter(
        student=request.user,
        batch_year=current_batch
    ).first()
    
    if existing_project:
        messages.info(request, 'You already have a project for this batch.')
        return redirect('projects:project_detail', pk=existing_project.pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = request.user
            project.batch_year = current_batch
            project.status = 'draft'
            project.save()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='created',
                details=f'Project "{project.title}" created'
            )
            
            messages.success(request, 'Project created successfully!')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
        'title': 'Create Project - PrimeTime',
        
        # Student info from new User model - UPDATED
        'student_id': request.user.user_id,
        'department': request.user.department,
        'batch_year': request.user.batch_year,
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_edit(request, pk):
    """Edit existing project (students only, draft/rejected status) - UPDATED"""
    
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions
    if request.user != project.student:
        return HttpResponseForbidden("You don't have permission to edit this project.")
    
    if not project.is_editable:
        messages.error(request, 'This project cannot be edited in its current status.')
        return redirect('projects:project_detail', pk=project.pk)
    
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
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'title': f'Edit Project - {project.title}',
        
        # Student info from new User model - UPDATED
        'student_id': request.user.user_id,
        'department': request.user.department,
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_detail(request, pk):
    """View project details - UPDATED"""
    
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions - UPDATED with new role properties
    can_edit = request.user == project.student and project.is_editable
    can_review = request.user.is_admin and project.status == 'pending'
    can_manage_deliverables = request.user == project.supervisor
    
    # Check if user has access to view this project
    has_access = (
        request.user == project.student or
        request.user == project.supervisor or
        request.user.is_admin
    )
    
    if not has_access:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:project_list')
    
    # Get deliverables
    deliverables = project.deliverables.all().order_by('stage')
    
    # Get activities
    activities = project.activities.all()[:10]
    
    context = {
        'project': project,
        'deliverables': deliverables,
        'activities': activities,
        'can_edit': can_edit,
        'can_review': can_review,
        'can_manage_deliverables': can_manage_deliverables,
        'title': project.title,
        
        # User role info - UPDATED
        'is_student': request.user.is_student,
        'is_supervisor': request.user.is_supervisor,
        'is_admin': request.user.is_admin,
        
        # Student info from new User model - UPDATED
        'student_id': project.student.user_id if project.student else None,
        'student_department': project.student.department if project.student else None,
    }
    return render(request, 'projects/project_detail.html', context)

# Add these to the existing views.py file

@login_required
def project_analytics(request, pk):
    """Project analytics dashboard"""
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions
    if request.user != project.student and not request.user.is_admin and request.user != project.supervisor:
        messages.error(request, 'You do not have permission to view these analytics.')
        return redirect('projects:project_detail', pk=project.pk)
    
    # Calculate analytics data
    deliverables = project.deliverables.all()
    completed_deliverables = deliverables.filter(is_approved=True).count()
    total_deliverables = 5  # Total possible deliverables
    
    # Calculate average marks
    approved_deliverables = deliverables.filter(is_approved=True, marks__isnull=False)
    if approved_deliverables.exists():
        average_marks = sum(d.marks for d in approved_deliverables) / approved_deliverables.count()
    else:
        average_marks = 0
    
    # Placeholder data for charts
    context = {
        'project': project,
        'title': f'Analytics - {project.title}',
        'progress_percentage': project.progress_percentage,
        'completed_deliverables': completed_deliverables,
        'total_deliverables': total_deliverables,
        'completion_rate': int((completed_deliverables / total_deliverables) * 100) if total_deliverables > 0 else 0,
        'average_marks': average_marks,
        'days_remaining': 30,  # Placeholder
        
        # Chart data (placeholders)
        'progress_timeline_labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Current'],
        'progress_timeline_data': [10, 25, 45, 70, project.progress_percentage],
        'expected_progress_data': [20, 40, 60, 80, 100],
        'deliverable_progress': min(100, int((completed_deliverables / total_deliverables) * 100)),
        'marks_progress': min(100, int(average_marks)),
        'activity_progress': min(100, project.progress_percentage),
        'deliverable_labels': ['Proposal', 'Mid Defense', 'Pre Defense', 'Final Defense', 'Documentation'],
        'deliverable_marks': [85, 78, 92, 0, 0],  # Placeholder
        'activity_heatmap_data': [],  # Placeholder
        
        # Insights and recommendations
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

@login_required
def project_recommendations(request, pk):
    """AI-powered project recommendations"""
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions
    if request.user != project.student:
        messages.error(request, 'Access denied.')
        return redirect('projects:project_detail', pk=project.pk)
    
    # Placeholder recommendation data
    context = {
        'project': project,
        'title': f'Recommendations - {project.title}',
        'total_recommendations': 12,
        'match_score': 85,
        'trending_count': 5,
        'high_rated_count': 8,
        'categories': [
            ('tutorial', 'Tutorials'),
            ('documentation', 'Documentation'),
            ('video', 'Videos'),
            ('article', 'Articles'),
            ('tool', 'Tools')
        ],
        
        # Placeholder recommendations
        'tech_recommendations': [
            {
                'id': 1,
                'category': 'tutorial',
                'category_icon': 'bx-video',
                'title': f'{project.languages_list[0]} Best Practices Tutorial',
                'description': 'Learn advanced techniques and best practices for your project.',
                'match_percentage': 92,
                'programming_languages': project.programming_languages,
                'tech_list': project.languages_list[:3],
                'average_rating': 4.5,
                'views': 1250,
                'like_count': 89,
                'recommendation_reason': 'Matches your technology stack perfectly',
                'url': '#'
            }
        ] if project.languages_list else [],
        
        'collaborative_recommendations': [
            {
                'id': 2,
                'category': 'documentation',
                'category_icon': 'bx-book',
                'title': 'Project Documentation Guide',
                'description': 'Comprehensive guide to writing effective project documentation.',
                'match_percentage': 78,
                'programming_languages': 'General',
                'tech_list': ['Documentation', 'Writing'],
                'average_rating': 4.2,
                'views': 890,
                'like_count': 45,
                'recommendation_reason': 'Popular among similar projects',
                'url': '#'
            }
        ],
        
        'trending_recommendations': [
            {
                'id': 3,
                'category': 'article',
                'category_icon': 'bx-news',
                'title': 'Latest Trends in Web Development',
                'description': 'Stay updated with the latest trends and technologies.',
                'match_percentage': 85,
                'programming_languages': 'Web, JavaScript',
                'tech_list': ['Web', 'JavaScript', 'Trends'],
                'average_rating': 4.7,
                'views': 2100,
                'like_count': 156,
                'recommendation_reason': 'Trending this week in your field',
                'url': '#'
            }
        ]
    }
    
    return render(request, 'projects/project_recommendations.html', context)

@login_required
def deliverable_submit(request, pk):
    """Submit project deliverable"""
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions
    if request.user != project.student:
        messages.error(request, 'Only the project student can submit deliverables.')
        return redirect('projects:project_detail', pk=project.pk)
    
    # For now, redirect to project detail with message
    messages.info(request, 'Deliverable submission feature will be implemented soon.')
    return redirect('projects:project_detail', pk=project.pk)

@login_required
def project_submit(request, pk):
    """Submit project for review (students only) - UPDATED"""
    
    project = get_object_or_404(Project, pk=pk)
    
    # Check permissions
    if request.user != project.student:
        return HttpResponseForbidden("You don't have permission to submit this project.")
    
    if project.status != 'draft':
        messages.error(request, 'Only draft projects can be submitted for review.')
        return redirect('projects:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        form = ProjectSubmitForm(request.POST)
        if form.is_valid():
            project.submit_for_review()
            
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                action='submitted',
                details='Project submitted for admin review'
            )
            
            messages.success(request, 'Project submitted for review successfully!')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectSubmitForm()
    
    context = {
        'form': form,
        'project': project,
        'title': 'Submit Project for Review',
        
        # Student info from new User model - UPDATED
        'student_id': request.user.user_id,
        'department': request.user.department,
    }
    return render(request, 'projects/project_submit.html', context)


@login_required
def project_review(request, pk):
    """Review project (admin only) - UPDATED"""
    
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
                
                # Log activity
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
                
                # Log activity
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
        
        # Student info from new User model - UPDATED
        'student_id': project.student.user_id if project.student else None,
        'student_department': project.student.department if project.student else None,
    }
    return render(request, 'projects/project_review.html', context)


@login_required
def project_list(request):
    """List all projects with filters - UPDATED"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    batch_filter = request.GET.get('batch', '')
    search_query = request.GET.get('q', '')
    
    # Build query
    projects = Project.objects.all().select_related('student', 'supervisor')
    
    # Apply filters based on user role - UPDATED with new role properties
    if request.user.is_student:
        projects = projects.filter(student=request.user)
    elif request.user.is_supervisor:
        projects = projects.filter(supervisor=request.user)
    # admin can see all projects
    
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
    
    # Add pagination
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
        
        # User role info - UPDATED
        'is_student': request.user.is_student,
        'is_supervisor': request.user.is_supervisor,
        'is_admin': request.user.is_admin,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_assign_supervisor(request, pk):
    """Assign supervisor to project (admin only) - NEW"""
    
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
            
            # Log activity
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
    """Supervisor's projects dashboard - UPDATED"""
    
    if not request.user.is_supervisor:
        messages.error(request, 'Access denied. Supervisors only.')
        return redirect('dashboard:home')
    
    # Get supervisor's projects
    projects = Project.objects.filter(supervisor=request.user).select_related('student')
    
    # Filter parameters
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
        
        # Supervisor info from new User model - UPDATED
        'department': request.user.department,
    }
    
    return render(request, 'projects/supervisor_projects.html', context)