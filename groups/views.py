# File: groups/views.py - COMPLETE UPDATED VERSION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, F
from django.http import JsonResponse
from django.utils import timezone

from .models import Group, GroupMembership, GroupActivity
from .forms import (
    GroupForm, AddStudentForm, BulkAddStudentsForm, 
    GroupFilterForm, QuickGroupCreateForm
)
from .utils import get_current_batch_year
from accounts.models import User
from projects.models import Project, GroupMeeting


@login_required
def group_list(request):
    """List all groups with filtering"""
    groups = Group.objects.all().select_related('supervisor').annotate(
        member_count=Count('members', filter=Q(members__is_active=True))
    )

    # Apply filters
    filter_form = GroupFilterForm(request.GET)
    if filter_form.is_valid():
        batch_year = filter_form.cleaned_data.get('batch_year')
        supervisor = filter_form.cleaned_data.get('supervisor')
        status = filter_form.cleaned_data.get('status')

        if batch_year:
            groups = groups.filter(batch_year=batch_year)
        if supervisor:
            groups = groups.filter(supervisor=supervisor)
        if status:
            if status == 'active':
                groups = groups.filter(is_active=True)
            elif status == 'inactive':
                groups = groups.filter(is_active=False)
            elif status == 'full':
                # Get groups where member count >= max_students
                full_group_ids = []
                for g in groups:
                    if g.is_full:
                        full_group_ids.append(g.id)
                groups = groups.filter(id__in=full_group_ids)
            elif status == 'needs_students':
                # Get groups where member count < min_students
                needs_students_ids = []
                for g in groups:
                    if g.student_count < g.min_students:
                        needs_students_ids.append(g.id)
                groups = groups.filter(id__in=needs_students_ids)

    # Role-based filtering
    if request.user.role == 'supervisor':
        groups = groups.filter(supervisor=request.user)
    elif request.user.role == 'student':
        # Students can see their own group
        student_groups = groups.filter(
            members__student=request.user, 
            members__is_active=True
        )
        if student_groups.exists():
            groups = student_groups

    # Calculate statistics
    total_students = sum(g.student_count for g in groups)
    full_groups = sum(1 for g in groups if g.is_full)
    active_groups = groups.filter(is_active=True).count()

    context = {
        'groups': groups,
        'filter_form': filter_form,
        'can_create': request.user.role in ['admin', 'superuser'] or request.user.is_superuser,
        'total_students': total_students,
        'full_groups': full_groups,
        'active_groups': active_groups,
        'current_batch_year': get_current_batch_year(),
    }
    return render(request, 'groups/group_list.html', context)


@login_required
def group_create(request):
    """Create a new group (Admin only) - Improved version"""
    if not (request.user.role in ['admin'] or request.user.is_superuser):
        messages.error(request, "You don't have permission to create groups")
        return redirect('groups:group_list')

    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()

            # Log activity
            GroupActivity.objects.create(
                group=group,
                user=request.user,
                action='created',
                details=f"Group created by {request.user.display_name}"
            )

            # Add students if selected
            add_students = form.cleaned_data.get('add_students', [])
            if add_students:
                added_count = 0
                for student in add_students:
                    try:
                        group.add_student(student, added_by=request.user)
                        added_count += 1
                    except Exception as e:
                        messages.warning(request, f"Could not add {student.display_name}: {str(e)}")
                
                if added_count > 0:
                    messages.success(
                        request, 
                        f"Group '{group.name}' created with {added_count} student(s)!"
                    )
            else:
                messages.success(request, f"Group '{group.name}' created successfully!")

            return redirect('groups:group_detail', pk=group.pk)
    else:
        form = GroupForm()

    return render(request, 'groups/group_form.html', {
        'form': form,
        'title': 'Create New Group',
        'is_creating': True,
    })


@login_required
def quick_create_group(request):
    """Quick create group by assigning supervisor"""
    if not (request.user.role in ['admin'] or request.user.is_superuser):
        messages.error(request, "You don't have permission to create groups")
        return redirect('groups:group_list')

    if request.method == 'POST':
        form = QuickGroupCreateForm(request.POST)
        if form.is_valid():
            supervisor = form.cleaned_data['supervisor']
            batch_year = form.cleaned_data['batch_year']
            group_name = form.cleaned_data.get('group_name')
            
            # Auto-generate name if not provided
            if not group_name:
                # Find next available letter for this supervisor
                existing_groups = Group.objects.filter(
                    supervisor=supervisor,
                    batch_year=batch_year
                )
                
                # Generate name like "Dr. Smith's Group" or "Group A", "Group B", etc.
                supervisor_last_name = supervisor.last_name or supervisor.username
                group_name = f"{supervisor_last_name}'s Group"
                
                # If that exists, try Group A, B, C...
                if existing_groups.filter(name=group_name).exists():
                    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                        test_name = f"Group {letter}"
                        if not existing_groups.filter(name=test_name).exists():
                            group_name = test_name
                            break
            
            # Create the group
            group = Group.objects.create(
                name=group_name,
                supervisor=supervisor,
                batch_year=batch_year,
                min_students=5,
                max_students=7,
                is_active=True,
                created_by=request.user
            )
            
            # Log activity
            GroupActivity.objects.create(
                group=group,
                user=request.user,
                action='created',
                details=f"Group quick-created by {request.user.display_name}"
            )
            
            messages.success(
                request,
                f"Group '{group.name}' created for {supervisor.display_name}!"
            )
            return redirect('groups:add_student', pk=group.pk)
    else:
        form = QuickGroupCreateForm()

    return render(request, 'groups/quick_create_group.html', {
        'form': form,
        'title': 'Quick Create Group'
    })


@login_required
def group_detail(request, pk):
    """View group details"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    if request.user.role == 'supervisor' and group.supervisor != request.user:
        messages.error(request, "You can only view your own groups")
        return redirect('groups:group_list')
    elif request.user.role == 'student':
        # Students can only view if they're in the group
        is_member = GroupMembership.objects.filter(
            group=group,
            student=request.user,
            is_active=True
        ).exists()
        if not is_member:
            messages.error(request, "You can only view groups you're a member of")
            return redirect('groups:group_list')

    # Get members
    members = group.members.filter(is_active=True).select_related('student')

    # Get group's project if exists
    project = Project.objects.filter(
        student__in=[m.student for m in members]
    ).first()

    # Get recent activities
    activities = group.activities.all()[:10]

    # Get meetings
    upcoming_meetings = GroupMeeting.objects.filter(
        group=group,
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    ).order_by('scheduled_date')
    
    past_meetings = GroupMeeting.objects.filter(
        group=group,
        status='completed'
    ).order_by('-scheduled_date')[:5]

    context = {
        'group': group,
        'members': members,
        'project': project,
        'activities': activities,
        'upcoming_meetings': upcoming_meetings,
        'past_meetings': past_meetings,
        'can_edit': request.user.role in ['admin'] or request.user.is_superuser or (
            request.user.role == 'supervisor' and group.supervisor == request.user
        ),
        'can_add_students': (
            request.user.role in ['admin'] or request.user.is_superuser or 
            (request.user.role == 'supervisor' and group.supervisor == request.user)
        ),
    }
    return render(request, 'groups/group_detail.html', context)


@login_required
def group_update(request, pk):
    """Update group details"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    if not (request.user.role in ['admin'] or request.user.is_superuser):
        if request.user.role == 'supervisor' and group.supervisor != request.user:
            messages.error(request, "You can only edit your own groups")
            return redirect('groups:group_detail', pk=pk)
        elif request.user.role == 'student':
            messages.error(request, "Students cannot edit groups")
            return redirect('groups:group_detail', pk=pk)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            old_supervisor = group.supervisor
            group = form.save()

            # Log supervisor change if applicable
            if old_supervisor != group.supervisor:
                GroupActivity.objects.create(
                    group=group,
                    user=request.user,
                    action='supervisor_changed',
                    details=f"Supervisor changed from {old_supervisor.display_name} to {group.supervisor.display_name}"
                )

            messages.success(request, f"Group '{group.name}' updated successfully!")
            return redirect('groups:group_detail', pk=group.pk)
    else:
        form = GroupForm(instance=group)

    return render(request, 'groups/group_form.html', {
        'form': form,
        'group': group,
        'title': f'Edit Group: {group.name}',
        'is_creating': False,
    })


@login_required
def group_delete(request, pk):
    """Delete a group (Admin only)"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "Only administrators can delete groups")
        return redirect('groups:group_detail', pk=pk)

    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f"Group '{group_name}' deleted successfully!")
        return redirect('groups:group_list')

    return render(request, 'groups/group_confirm_delete.html', {'group': group})


@login_required
def add_student(request, pk):
    """Add a student to a group"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    can_add = (
        request.user.role in ['admin'] or 
        request.user.is_superuser or
        (request.user.role == 'supervisor' and group.supervisor == request.user)
    )
    
    if not can_add:
        messages.error(request, "You don't have permission to add students to this group")
        return redirect('groups:group_detail', pk=pk)

    if group.is_full:
        messages.error(request, "This group is already full")
        return redirect('groups:group_detail', pk=pk)

    if request.method == 'POST':
        form = AddStudentForm(request.POST, group=group)
        if form.is_valid():
            student = form.cleaned_data['student']
            try:
                group.add_student(student, added_by=request.user)
                messages.success(
                    request, 
                    f"{student.display_name} added to group successfully!"
                )
                return redirect('groups:group_detail', pk=pk)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = AddStudentForm(group=group)

    return render(request, 'groups/add_student.html', {
        'form': form,
        'group': group
    })


@login_required
def bulk_add_students(request, pk):
    """Add multiple students to a group at once"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    can_add = (
        request.user.role in ['admin'] or 
        request.user.is_superuser or
        (request.user.role == 'supervisor' and group.supervisor == request.user)
    )
    
    if not can_add:
        messages.error(request, "You don't have permission to add students to this group")
        return redirect('groups:group_detail', pk=pk)

    if request.method == 'POST':
        form = BulkAddStudentsForm(request.POST, group=group)
        if form.is_valid():
            students = form.cleaned_data['students']
            added_count = 0
            failed_students = []

            for student in students:
                if group.is_full:
                    messages.warning(
                        request, 
                        f"Group is now full. Could not add remaining students."
                    )
                    break

                try:
                    group.add_student(student, added_by=request.user)
                    added_count += 1
                except Exception as e:
                    failed_students.append(f"{student.display_name}: {str(e)}")

            if added_count > 0:
                messages.success(request, f"{added_count} student(s) added successfully!")

            if failed_students:
                for error in failed_students:
                    messages.error(request, error)

            return redirect('groups:group_detail', pk=pk)
    else:
        form = BulkAddStudentsForm(group=group)

    return render(request, 'groups/bulk_add_students.html', {
        'form': form,
        'group': group
    })


@login_required
def remove_student(request, pk, student_id):
    """Remove a student from a group"""
    group = get_object_or_404(Group, pk=pk)
    student = get_object_or_404(User, pk=student_id, role='student')

    # Check permissions
    can_remove = (
        request.user.role in ['admin'] or 
        request.user.is_superuser or
        (request.user.role == 'supervisor' and group.supervisor == request.user)
    )
    
    if not can_remove:
        messages.error(request, "You don't have permission to remove students")
        return redirect('groups:group_detail', pk=pk)

    if request.method == 'POST':
        if group.remove_student(student, removed_by=request.user):
            messages.success(request, f"{student.display_name} removed from group")
        else:
            messages.error(request, "Student is not in this group")
        
        return redirect('groups:group_detail', pk=pk)

    return render(request, 'groups/confirm_remove_student.html', {
        'group': group,
        'student': student
    })


@login_required
def my_group(request):
    """View current user's group (for students AND supervisors)"""
    
    # For students
    if request.user.role == 'student':
        try:
            membership = GroupMembership.objects.get(
                student=request.user,
                is_active=True
            )
            return redirect('groups:group_detail', pk=membership.group.pk)
        except GroupMembership.DoesNotExist:
            messages.info(request, "You are not currently in any group")
            return redirect('groups:group_list')
    
    # For supervisors
    elif request.user.role == 'supervisor':
        try:
            # Get the first active group for this supervisor
            group = Group.objects.filter(
                supervisor=request.user,
                is_active=True
            ).first()
            
            if group:
                return redirect('groups:group_detail', pk=group.pk)
            else:
                messages.info(request, "You don't have any active groups assigned yet.")
                return redirect('groups:group_list')
        except Exception as e:
            messages.error(request, f"Error accessing group: {str(e)}")
            return redirect('groups:group_list')
    
    # For admins or others
    else:
        messages.info(request, "View your groups from the groups list")
        return redirect('groups:group_list')


@login_required
def group_activities(request, pk):
    """View all activities for a group"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    if request.user.role == 'supervisor' and group.supervisor != request.user:
        messages.error(request, "You can only view activities for your own groups")
        return redirect('groups:group_list')
    elif request.user.role == 'student':
        is_member = GroupMembership.objects.filter(
            group=group,
            student=request.user,
            is_active=True
        ).exists()
        if not is_member:
            messages.error(request, "You can only view activities for your own group")
            return redirect('groups:group_list')

    activities = group.activities.all()

    return render(request, 'groups/group_activities.html', {
        'group': group,
        'activities': activities
    })


# AJAX Views

@login_required
def get_available_students(request):
    """AJAX endpoint to get students not in any group"""
    if not (request.user.role in ['admin', 'supervisor'] or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Get students not in any active group
    existing_student_ids = GroupMembership.objects.filter(
        is_active=True
    ).values_list('student_id', flat=True)

    available_students = User.objects.filter(
        role='student',
        is_active=True
    ).exclude(id__in=existing_student_ids).values(
        'id', 'username', 'first_name', 'last_name', 'department'
    )

    students_list = [
        {
            'id': s['id'],
            'name': f"{s['first_name']} {s['last_name']}" if s['first_name'] else s['username'],
            'username': s['username'],
            'department': s['department'] or 'No Department'
        }
        for s in available_students
    ]

    return JsonResponse({'students': students_list})