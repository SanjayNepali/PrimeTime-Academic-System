# File: groups/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, F
from django.http import JsonResponse

from .models import Group, GroupMembership, GroupActivity
from .forms import GroupForm, AddStudentForm, BulkAddStudentsForm, GroupFilterForm
from accounts.models import User
from projects.models import Project


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
                groups = groups.filter(is_active=True, is_full=False)
            elif status == 'inactive':
                groups = groups.filter(is_active=False)
            elif status == 'full':
                groups = groups.filter(is_full=True)
            elif status == 'needs_students':
                groups = groups.filter(is_active=True).annotate(
                    count=Count('members', filter=Q(members__is_active=True))
                ).filter(count__lt=F('min_students'))

    # Role-based filtering
    if request.user.role == 'supervisor':
        groups = groups.filter(supervisor=request.user)
    elif request.user.role == 'student':
        # Students can see their own group or all groups if not in one
        student_groups = groups.filter(members__student=request.user, members__is_active=True)
        if student_groups.exists():
            groups = student_groups
        # Otherwise show all groups (for browsing)

    context = {
        'groups': groups,
        'filter_form': filter_form,
        'can_create': request.user.role in ['admin', 'supervisor'],
    }
    return render(request, 'groups/group_list.html', context)


@login_required
def group_create(request):
    """Create a new group (Admin only)"""
    if request.user.role not in ['admin']:
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
                details=f"Group created by {request.user.get_full_name()}"
            )

            messages.success(request, f"Group '{group.name}' created successfully!")
            return redirect('groups:group_detail', pk=group.pk)
    else:
        form = GroupForm()

    return render(request, 'groups/group_form.html', {
        'form': form,
        'title': 'Create New Group'
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
        if not is_member and request.user.role == 'student':
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

    context = {
        'group': group,
        'members': members,
        'project': project,
        'activities': activities,
        'can_edit': request.user.role in ['admin'] or (request.user.role == 'supervisor' and group.supervisor == request.user),
        'can_add_students': request.user.role in ['admin', 'supervisor'] and group.supervisor == request.user,
    }
    return render(request, 'groups/group_detail.html', context)


@login_required
def group_update(request, pk):
    """Update group details"""
    group = get_object_or_404(Group, pk=pk)

    # Check permissions
    if request.user.role not in ['admin']:
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
                    details=f"Supervisor changed from {old_supervisor.get_full_name()} to {group.supervisor.get_full_name()}"
                )

            messages.success(request, f"Group '{group.name}' updated successfully!")
            return redirect('groups:group_detail', pk=group.pk)
    else:
        form = GroupForm(instance=group)

    return render(request, 'groups/group_form.html', {
        'form': form,
        'group': group,
        'title': f'Edit Group: {group.name}'
    })


@login_required
def group_delete(request, pk):
    """Delete a group (Admin only)"""
    if request.user.role != 'admin':
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
    if request.user.role not in ['admin', 'supervisor'] or (request.user.role == 'supervisor' and group.supervisor != request.user):
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
                group.add_student(student)

                # Log activity
                GroupActivity.objects.create(
                    group=group,
                    user=request.user,
                    action='student_added',
                    details=f"{student.get_full_name()} added to group by {request.user.get_full_name()}"
                )

                messages.success(request, f"{student.get_full_name()} added to group successfully!")
                return redirect('groups:group_detail', pk=pk)
            except ValidationError as e:
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
    if request.user.role not in ['admin', 'supervisor'] or (request.user.role == 'supervisor' and group.supervisor != request.user):
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
                    messages.warning(request, f"Group is now full. Could not add remaining students.")
                    break

                try:
                    group.add_student(student)
                    added_count += 1

                    # Log activity
                    GroupActivity.objects.create(
                        group=group,
                        user=request.user,
                        action='student_added',
                        details=f"{student.get_full_name()} added to group (bulk add)"
                    )
                except ValidationError as e:
                    failed_students.append(f"{student.get_full_name()}: {str(e)}")

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
    if request.user.role not in ['admin', 'supervisor'] or (request.user.role == 'supervisor' and group.supervisor != request.user):
        messages.error(request, "You don't have permission to remove students from this group")
        return redirect('groups:group_detail', pk=pk)

    if request.method == 'POST':
        try:
            group.remove_student(student)

            # Log activity
            GroupActivity.objects.create(
                group=group,
                user=request.user,
                action='student_removed',
                details=f"{student.get_full_name()} removed from group by {request.user.get_full_name()}"
            )

            messages.success(request, f"{student.get_full_name()} removed from group")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('groups:group_detail', pk=pk)

    return render(request, 'groups/confirm_remove_student.html', {
        'group': group,
        'student': student
    })


@login_required
def my_group(request):
    """View current user's group (for students)"""
    if request.user.role != 'student':
        messages.error(request, "This page is only for students")
        return redirect('groups:group_list')

    try:
        membership = GroupMembership.objects.get(
            student=request.user,
            is_active=True
        )
        return redirect('groups:group_detail', pk=membership.group.pk)
    except GroupMembership.DoesNotExist:
        messages.info(request, "You are not currently in any group")
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
    if request.user.role not in ['admin', 'supervisor']:
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
