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
    """Student's own project view with resources, forum, and help - UPDATED"""
    
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
    
    # Get project resources and recommendations
    resources = []
    if project:
        # Get resources based on project languages
        # This will be enhanced with recommendation engine
        # Note: You'll need to import Resource model if it exists
        # resources = Resource.objects.filter(
        #     tags__name__in=project.languages_list
        # ).distinct()[:10]
        pass
    
    # Get forum posts related to student's technologies
    forum_posts = []
    if project:
        # Note: You'll need to import ForumPost model if it exists
        # forum_posts = ForumPost.objects.filter(
        #     Q(tags__name__in=project.languages_list) |
        #     Q(author=request.user)
        # ).distinct().order_by('-created_at')[:10]
        pass
    
    context = {
        'title': 'My Project - PrimeTime',
        'project': project,
        'resources': resources,
        'forum_posts': forum_posts,
        'can_edit': project and project.status in ['draft', 'rejected'],
        'show_resubmit': project and project.status == 'rejected',
        'tab': request.GET.get('tab', 'overview'),  # For tab navigation
        
        # Student info from new User model - UPDATED
        'student_id': request.user.user_id,
        'department': request.user.department,
        'batch_year': request.user.batch_year,
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
        'is_admin': request.user.is_admin,  # only admin now
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
    can_review = (request.user.is_superadmin or request.user.is_admin) and project.status == 'pending'
    can_manage_deliverables = request.user == project.supervisor
    
    # Check if user has access to view this project
    has_access = (
        request.user == project.student or
        request.user == project.supervisor or
        request.user.is_superadmin or
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
        'is_superadmin': request.user.is_superadmin,
        
        # Student info from new User model - UPDATED
        'student_id': project.student.user_id if project.student else None,
        'student_department': project.student.department if project.student else None,
    }
    return render(request, 'projects/project_detail.html', context)


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
    """Review project (admin/superadmin only) - UPDATED"""
    
    if not (request.user.is_admin or request.user.is_superadmin):
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
    # superadmin and admin can see all projects
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    if batch_filter:
        projects = projects.filter(batch_year=batch_filter)
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(programming_languages__icontains=search_query) |
            Q(student__full_name__icontains=search_query) |  # UPDATED: full_name
            Q(student__user_id__icontains=search_query)      # UPDATED: user_id
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
        'is_superadmin': request.user.is_superadmin,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_assign_supervisor(request, pk):
    """Assign supervisor to project (admin/superadmin only) - NEW"""
    
    if not (request.user.is_admin or request.user.is_superadmin):
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
            Q(student__full_name__icontains=search_query) |  # UPDATED: full_name
            Q(student__user_id__icontains=search_query)      # UPDATED: user_id
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