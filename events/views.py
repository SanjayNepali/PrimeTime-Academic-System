# File: events/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
import os

from .models import Event, EventAttendance, Calendar, Notification, EventSubmission
from .forms import EventForm, CalendarForm, EventSubmissionForm, EventDeadlineForm
from .notifications import notify_event_update, notify_event_cancelled
from analytics.forms import SupervisorReviewForm, AdminReviewForm
from accounts.models import User


@login_required
def event_list(request):
    """List all events with filtering"""
    print(f"\n=== USER CHECK ===")
    print(f"Logged in user: {request.user.username}")
    print(f"User ID: {request.user.id}")
    print(f"User email: {request.user.email}")
    print(f"User role: {request.user.role}")
    print(f"User batch_year: {request.user.batch_year}")
    print("=================\n")
    # Get all active events
    all_events = Event.objects.filter(is_active=True).select_related('organizer', 'group')
    print(f"1. Total active events in DB: {all_events.count()}")
    
    for event in all_events:
        print(f"   - '{event.title}' (ID: {event.id}, Type: {event.event_type}, Organizer: {event.organizer.username if event.organizer else 'None'}, Group: {event.group.name if event.group else 'None'})")
    
    # Start with all active events
    events = all_events
    
    # Filter by user role
    if request.user.role == 'student':
        print(f"\n2. Student filtering applied")
        events = events.filter(
            Q(participants=request.user) |
            Q(batch_year=request.user.batch_year) |
            Q(batch_year__isnull=True)
        ).distinct()
        print(f"   Events after student filter: {events.count()}")
        
    elif request.user.role == 'supervisor':
        print(f"\n2. Supervisor filtering applied for user: {request.user.username}")
        print(f"   User ID: {request.user.id}")
        
        # Debug: Check what groups this supervisor supervises
        from groups.models import Group
        supervised_groups = Group.objects.filter(supervisor=request.user)
        print(f"   Groups supervised by {request.user.username}: {[g.name for g in supervised_groups]}")
        
        # Original query
        original_query = events.filter(
            Q(organizer=request.user) |
            Q(group__supervisor=request.user) |
            Q(participants=request.user)
        ).distinct()
        
        print(f"   Events after original filter: {original_query.count()}")
        
        # Check each condition separately for debugging
        organized_events = events.filter(organizer=request.user)
        group_events = events.filter(group__supervisor=request.user)
        participant_events = events.filter(participants=request.user)
        
        print(f"   Events organized by {request.user.username}: {organized_events.count()}")
        print(f"   Events in groups supervised by {request.user.username}: {group_events.count()}")
        print(f"   Events where {request.user.username} is participant: {participant_events.count()}")
        
        # TEMPORARY: Show all events for supervisor for debugging
        print(f"\n3. TEMPORARY: Showing all events for supervisor debugging")
        events = all_events  # Remove filters temporarily
        
    elif request.user.role == 'admin':
        print(f"\n2. Admin - showing all events")
        events = all_events
    
    print(f"\n3. Events before time filter: {events.count()}")
    for event in events:
        print(f"   - '{event.title}' (Start: {event.start_datetime}, End: {event.end_datetime})")

    # Apply filters from query params
    event_type = request.GET.get('type')
    time_filter = request.GET.get('time', 'upcoming')

    if event_type:
        events = events.filter(event_type=event_type)
        print(f"4. After event_type filter ('{event_type}'): {events.count()}")

    now = timezone.now()
    print(f"\n5. Current time: {now}")
    print(f"   Time filter selected: '{time_filter}'")
    
    if time_filter == 'upcoming':
        events = events.filter(start_datetime__gte=now, is_cancelled=False)
        print(f"   Events after upcoming filter: {events.count()}")
        print(f"   Showing events starting from: {now}")
    elif time_filter == 'past':
        events = events.filter(end_datetime__lt=now)
        print(f"   Events after past filter: {events.count()}")
    elif time_filter == 'today':
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        events = events.filter(start_datetime__gte=today_start, start_datetime__lt=today_end)
        print(f"   Events after today filter: {events.count()}")
    elif time_filter == 'this_week':
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        events = events.filter(start_datetime__gte=week_start, start_datetime__lt=week_end)
        print(f"   Events after this_week filter: {events.count()}")

    # Debug final events
    print(f"\n6. FINAL events to display: {events.count()}")
    for event in events:
        print(f"   - '{event.title}' (ID: {event.id}, Start: {event.start_datetime}, End: {event.end_datetime})")
    print("=== END DEBUG ===\n")

    context = {
        'events': events.order_by('start_datetime'),
        'event_types': Event.EVENT_TYPES,
        'selected_type': event_type,
        'time_filter': time_filter,
        'can_create': request.user.role == 'admin',
        'can_schedule_meeting': request.user.role == 'supervisor',
    }
    return render(request, 'events/event_list.html', context)
@login_required
def event_create(request):
    """Create a new event - Only admin can create all events, supervisor can only create meetings for their groups"""
    if request.user.role == 'admin':
        # Admin can create any type of event
        if request.method == 'POST':
            form = EventForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.created_by = request.user
                if not event.organizer:
                    event.organizer = request.user
                event.save()
                form.save_m2m()

                # Notify participants
                participants = event.participants.all()
                if participants:
                    Notification.create_for_event(
                        event,
                        participants,
                        notification_type='event_update',
                        title=f"New Event: {event.title}",
                        message=f"You have been invited to '{event.title}' on {event.start_datetime.strftime('%B %d, %Y at %I:%M %p')}"
                    )

                messages.success(request, f"Event '{event.title}' created successfully!")
                return redirect('events:event_detail', pk=event.pk)
        else:
            form = EventForm()
        
        return render(request, 'events/event_form.html', {
            'form': form,
            'title': 'Create New Event'
        })
    
    elif request.user.role == 'supervisor':
        # Supervisors can only schedule group meetings
        # They should use the group meeting scheduler
        messages.info(request, "Supervisors can schedule group meetings from the Events page")
        return redirect('events:event_list')
    
    else:
        messages.error(request, "You don't have permission to create events")
        return redirect('events:event_list')

@login_required
def event_detail(request, pk):
    """View event details"""
    event = get_object_or_404(Event, pk=pk)

    # Check if user has access
    can_view = (
        request.user.role == 'admin' or
        request.user == event.organizer or
        event.participants.filter(pk=request.user.pk).exists() or
        (event.batch_year and request.user.batch_year == event.batch_year) or
        (event.group and event.group.supervisor == request.user)
    )

    if not can_view:
        messages.error(request, "You don't have access to this event")
        return redirect('events:event_list')

    # Get user's attendance record
    attendance = None
    user_rsvp_status = None
    if event.participants.filter(pk=request.user.pk).exists():
        attendance = EventAttendance.objects.filter(
            event=event,
            user=request.user
        ).first()
        if attendance:
            user_rsvp_status = attendance.status

    # Get all attendances for this event
    attendances = event.attendances.select_related('user').all()

    context = {
        'event': event,
        'attendance': attendance,
        'user_rsvp_status': user_rsvp_status,
        'attendees': [att.user for att in attendances.filter(status='confirmed')],
        'attendee_count': attendances.filter(status='confirmed').count(),
        'can_edit': request.user.role == 'admin' or request.user == event.organizer,
        'can_manage_attendance': request.user.role in ['admin', 'supervisor'] and request.user == event.organizer,
    }
    return render(request, 'events/event_detail.html', context)

@login_required
def event_update(request, pk):
    """Update event details"""
    event = get_object_or_404(Event, pk=pk)

    # Check permissions
    if request.user.role not in ['admin'] and request.user != event.organizer:
        messages.error(request, "You don't have permission to edit this event")
        return redirect('events:event_detail', pk=pk)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()

            # Notify participants about the update
            notify_event_update(event, f"The event '{event.title}' has been updated. Please check the details.")

            messages.success(request, f"Event '{event.title}' updated successfully!")
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {
        'form': form,
        'event': event,
        'title': f'Edit Event: {event.title}'
    })


@login_required
def event_delete(request, pk):
    """Delete an event"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can delete events")
        return redirect('events:event_detail', pk=pk)

    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        event_title = event.title
        event.delete()
        messages.success(request, f"Event '{event_title}' deleted successfully!")
        return redirect('events:event_list')

    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
def event_cancel(request, pk):
    """Cancel an event"""
    event = get_object_or_404(Event, pk=pk)

    # Check permissions
    if request.user.role not in ['admin'] and request.user != event.organizer:
        messages.error(request, "You don't have permission to cancel this event")
        return redirect('events:event_detail', pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        event.cancel(reason)

        # Notify participants
        notify_event_cancelled(event)

        messages.success(request, f"Event '{event.title}' has been cancelled")
        return redirect('events:event_detail', pk=pk)

    return render(request, 'events/event_cancel.html', {'event': event})

@login_required
def rsvp_event(request, pk):
    """RSVP to an event (confirm/decline)"""
    event = get_object_or_404(Event, pk=pk)

    # Check if user is invited
    if not event.participants.filter(pk=request.user.pk).exists():
        messages.error(request, "You are not invited to this event")
        return redirect('events:event_list')

    if request.method == 'POST':
        status = request.POST.get('status')
        attendance, created = EventAttendance.objects.get_or_create(
            event=event,
            user=request.user
        )

        if status == 'yes':
            attendance.confirm_attendance()
            messages.success(request, f"You have confirmed attendance for '{event.title}'")
        elif status == 'no':
            attendance.decline_attendance()
            messages.info(request, f"You have declined '{event.title}'")
        elif status == 'maybe':
            # You might want to add a 'maybe' status handling
            attendance.status = 'pending'
            attendance.rsvp_at = timezone.now()
            attendance.save()
            messages.info(request, f"You marked '{event.title}' as maybe")
        else:
            messages.error(request, "Invalid RSVP status")
    
    return redirect('events:event_detail', pk=pk)

@login_required
def my_events(request):
    """View user's personal events calendar"""
    now = timezone.now()

    # Get events user is invited to
    upcoming_events = Event.objects.filter(
        participants=request.user,
        start_datetime__gte=now,
        is_active=True,
        is_cancelled=False
    ).order_by('start_datetime')[:10]

    past_events = Event.objects.filter(
        participants=request.user,
        end_datetime__lt=now,
        is_active=True
    ).order_by('-start_datetime')[:10]

    # Get user's attendance records
    confirmed_events = EventAttendance.objects.filter(
        user=request.user,
        status='confirmed',
        event__start_datetime__gte=now
    ).select_related('event').order_by('event__start_datetime')

    context = {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'confirmed_events': confirmed_events,
    }
    return render(request, 'events/my_events.html', context)


@login_required
def calendar_list(request):
    """List all academic calendars"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can view calendars")
        return redirect('events:event_list')

    calendars = Calendar.objects.all().order_by('-batch_year')

    context = {
        'calendars': calendars,
    }
    return render(request, 'events/calendar_list.html', context)


@login_required
def calendar_create(request):
    """Create a new academic calendar"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can create calendars")
        return redirect('events:event_list')

    if request.method == 'POST':
        form = CalendarForm(request.POST)
        if form.is_valid():
            calendar = form.save(commit=False)
            calendar.created_by = request.user
            calendar.save()
            messages.success(request, f"Calendar '{calendar.name}' created successfully!")
            return redirect('events:calendar_list')
    else:
        form = CalendarForm()

    return render(request, 'events/calendar_form.html', {
        'form': form,
        'title': 'Create Academic Calendar'
    })


@login_required
def calendar_detail(request, pk):
    """View calendar details"""
    calendar = get_object_or_404(Calendar, pk=pk)
    return render(request, 'events/calendar_detail.html', {'calendar': calendar})


@login_required
def notifications_list(request):
    """List user's notifications"""
    # FIX: Don't slice before filtering
    notifications_qs = request.user.notifications.all().order_by('-created_at')
    
    # Mark as read if requested
    if request.GET.get('mark_all_read'):
        notifications_qs.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        messages.success(request, "All notifications marked as read")
        return redirect('events:notifications_list')
    
    # NOW slice after filtering is done
    notifications = notifications_qs[:50]
    
    # Calculate unread count from original queryset
    unread_count = notifications_qs.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'title': 'System Notifications'
    }
    return render(request, 'events/notifications_list.html', context)
@login_required
def notification_mark_read(request, pk):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()

    # Redirect to the notification's link if provided
    if notification.link_url:
        return redirect(notification.link_url)
    return redirect('events:notifications_list')


# AJAX Views

@login_required
def get_unread_notifications(request):
    """AJAX endpoint to get unread notifications count"""
    if request.user.is_authenticated:
        # FIX: Don't slice before converting to values
        unread_qs = request.user.notifications.filter(is_read=False)
        unread_count = unread_qs.count()
        
        # Now slice for recent notifications
        recent_notifications = list(
            unread_qs[:5].values(
                'id', 'title', 'message', 'notification_type', 'created_at'
            )
        )
        
        return JsonResponse({
            'unread_count': unread_count,
            'notifications': recent_notifications
        })
    return JsonResponse({'unread_count': 0, 'notifications': []})

# File: events/views.py (update event_calendar_view function)
@login_required
def event_calendar_view(request):
    """Calendar view of events - SIMPLE VERSION"""
    print(f"\n=== CALENDAR SIMPLE DEBUG ===")
    
    # Get ALL events
    events = Event.objects.filter(is_active=True, is_cancelled=False)
    print(f"Total events: {events.count()}")
    
    # Simple events data
    events_data = []
    for event in events:
        events_data.append({
            'id': event.pk,
            'title': event.title,
            'start': event.start_datetime.isoformat(),
            'end': event.end_datetime.isoformat(),
            'url': f'/events/{event.pk}/',
            'color': '#60a5fa',  # Simple blue for all
        })
        print(f"Added: {event.title} at {event.start_datetime}")
    
    print(f"Events in JSON: {len(events_data)}")
    
    context = {
        'events_json': events_data,
        'current_month': timezone.now().strftime('%B %Y'),
    }
    return render(request, 'events/calendar_view.html', context)
# ========== EVENT SUBMISSION VIEWS ==========

@login_required
def submit_to_event(request, event_id):
    """Student submits file to a deadline event"""
    if request.user.role != 'student':
        messages.error(request, "Only students can submit to events")
        return redirect('events:event_detail', pk=event_id)

    event = get_object_or_404(Event, pk=event_id, event_type='deadline', requires_submission=True)

    # Check if event has passed
    if timezone.now() > event.end_datetime:
        messages.warning(request, "This event deadline has passed. Late submissions may incur penalties.")

    # Check if student has already submitted (get latest version)
    existing_submission = EventSubmission.objects.filter(
        event=event,
        student=request.user
    ).order_by('-version').first()

    # Don't allow new submission if already approved by admin
    if existing_submission and existing_submission.status == 'admin_approved':
        messages.info(request, "Your submission has already been approved. No further submissions allowed.")
        return redirect('events:my_submissions')

    if request.method == 'POST':
        form = EventSubmissionForm(request.POST, request.FILES, event=event)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.event = event
            submission.student = request.user
            submission.submission_date = timezone.now()

            # Determine version number
            if existing_submission:
                submission.version = existing_submission.version + 1
                submission.parent_submission = existing_submission
                submission.status = 'resubmitted'
            else:
                submission.version = 1
                submission.status = 'pending'

            # Check if submission is late
            if timezone.now() > event.end_datetime:
                submission.late_submission = True
                submission.late_penalty = event.late_submission_penalty

            # Extract file type
            if submission.submission_file:
                submission.file_type = os.path.splitext(submission.submission_file.name)[1][1:].upper()

            submission.save()

            # Notify supervisor
            from projects.models import Project
            try:
                project = Project.objects.get(student=request.user)
                if project.supervisor:
                    Notification.objects.create(
                        recipient=project.supervisor,
                        notification_type='event_update',
                        title=f"New Submission from {request.user.display_name}",
                        message=f"{request.user.display_name} submitted to '{event.title}'. Please review.",
                        link_url=f'/events/submissions/review/{submission.pk}/'
                    )
            except Project.DoesNotExist:
                pass

            messages.success(request, f"Submission uploaded successfully! (Version {submission.version})")
            return redirect('events:my_submissions')
    else:
        form = EventSubmissionForm(event=event)

    context = {
        'form': form,
        'event': event,
        'existing_submission': existing_submission,
    }
    return render(request, 'events/submit_to_event.html', context)


@login_required
def my_submissions(request):
    """Student views their event submissions"""
    if request.user.role != 'student':
        messages.error(request, "Only students can view submissions")
        return redirect('dashboard:home')

    # Get all submissions by this student
    submissions = EventSubmission.objects.filter(
        student=request.user
    ).select_related('event').order_by('-submission_date')

    # Get pending deadline events requiring submission
    upcoming_deadlines = Event.objects.filter(
        event_type='deadline',
        requires_submission=True,
        is_active=True,
        is_cancelled=False,
        end_datetime__gte=timezone.now()
    ).exclude(
        submissions__student=request.user,
        submissions__status='admin_approved'
    ).order_by('end_datetime')

    context = {
        'submissions': submissions,
        'upcoming_deadlines': upcoming_deadlines,
    }
    return render(request, 'events/my_submissions.html', context)


@login_required
def supervisor_review_submissions(request):
    """Supervisor reviews pending submissions from their students"""
    if request.user.role != 'supervisor':
        messages.error(request, "Only supervisors can access this page")
        return redirect('dashboard:home')

    # Get submissions from students supervised by this user
    from projects.models import Project
    supervised_students = Project.objects.filter(
        supervisor=request.user
    ).values_list('student_id', flat=True)

    # Get submissions pending supervisor review or resubmitted
    pending_submissions = EventSubmission.objects.filter(
        student_id__in=supervised_students,
        status__in=['pending', 'resubmitted', 'supervisor_review']
    ).select_related('event', 'student').order_by('event__end_datetime', '-submission_date')

    # Get submissions already reviewed by supervisor
    reviewed_submissions = EventSubmission.objects.filter(
        student_id__in=supervised_students,
        status__in=['supervisor_approved', 'supervisor_rejected', 'admin_review', 'admin_approved', 'admin_rejected']
    ).select_related('event', 'student').order_by('-supervisor_reviewed_at')[:20]

    context = {
        'pending_submissions': pending_submissions,
        'reviewed_submissions': reviewed_submissions,
    }
    return render(request, 'events/supervisor_review_submissions.html', context)


@login_required
def supervisor_review_submission_detail(request, submission_id):
    """Supervisor reviews a specific submission"""
    if request.user.role != 'supervisor':
        messages.error(request, "Only supervisors can review submissions")
        return redirect('dashboard:home')

    submission = get_object_or_404(EventSubmission, pk=submission_id)

    # Check if supervisor supervises this student
    from projects.models import Project
    try:
        project = Project.objects.get(student=submission.student, supervisor=request.user)
    except Project.DoesNotExist:
        messages.error(request, "You don't supervise this student")
        return redirect('events:supervisor_review_submissions')

    if request.method == 'POST':
        form = SupervisorReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            rating = form.cleaned_data.get('rating')

            if action == 'approve':
                submission.supervisor_approve(remarks=remarks, rating=int(rating) if rating else None)
                messages.success(request, "Submission approved! It has been sent to admin for final review.")

                # Notify admin
                admins = User.objects.filter(role='admin')
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        notification_type='event_update',
                        title=f"Submission Approved by Supervisor",
                        message=f"Submission from {submission.student.display_name} for '{submission.event.title}' is ready for final review.",
                        link_url=f'/events/submissions/admin-review/{submission.pk}/'
                    )
            else:
                submission.supervisor_reject(remarks=remarks)
                messages.info(request, "Submission rejected. Student has been notified.")

                # Notify student
                Notification.objects.create(
                    recipient=submission.student,
                    notification_type='event_update',
                    title=f"Submission Needs Revision",
                    message=f"Your submission for '{submission.event.title}' needs revision. Check supervisor remarks.",
                    link_url=f'/events/my-submissions/'
                )

            return redirect('events:supervisor_review_submissions')
    else:
        form = SupervisorReviewForm()

    context = {
        'submission': submission,
        'form': form,
        'project': project,
    }
    return render(request, 'events/review_submission_detail.html', context)


@login_required
def admin_review_submissions(request):
    """Admin reviews submissions approved by supervisors"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can access this page")
        return redirect('dashboard:home')

    # Get submissions pending admin review
    pending_submissions = EventSubmission.objects.filter(
        status__in=['supervisor_approved', 'admin_review']
    ).select_related('event', 'student').order_by('event__end_datetime', '-supervisor_reviewed_at')

    # Get submissions already reviewed by admin
    reviewed_submissions = EventSubmission.objects.filter(
        status__in=['admin_approved', 'admin_rejected']
    ).select_related('event', 'student').order_by('-admin_reviewed_at')[:30]

    # Statistics
    total_submissions = EventSubmission.objects.count()
    approved_count = EventSubmission.objects.filter(status='admin_approved').count()
    rejected_count = EventSubmission.objects.filter(status__in=['supervisor_rejected', 'admin_rejected']).count()

    context = {
        'pending_submissions': pending_submissions,
        'reviewed_submissions': reviewed_submissions,
        'total_submissions': total_submissions,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'events/admin_review_submissions.html', context)


@login_required
def admin_review_submission_detail(request, submission_id):
    """Admin gives final approval/rejection"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can review submissions")
        return redirect('dashboard:home')

    submission = get_object_or_404(EventSubmission, pk=submission_id)

    if request.method == 'POST':
        form = AdminReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            rating = form.cleaned_data.get('rating')

            if action == 'approve':
                submission.admin_approve(remarks=remarks, rating=int(rating) if rating else None)
                messages.success(request, "Submission approved! Student has been notified.")

                # Notify student
                Notification.objects.create(
                    recipient=submission.student,
                    notification_type='event_update',
                    title=f"Submission Approved!",
                    message=f"Your submission for '{submission.event.title}' has been approved by administration.",
                    link_url=f'/events/my-submissions/'
                )
            else:
                submission.admin_reject(remarks=remarks)
                messages.info(request, "Submission rejected. Student has been notified.")

                # Notify student and supervisor
                Notification.objects.create(
                    recipient=submission.student,
                    notification_type='event_update',
                    title=f"Submission Rejected",
                    message=f"Your submission for '{submission.event.title}' was not approved. Check admin remarks.",
                    link_url=f'/events/my-submissions/'
                )

            return redirect('events:admin_review_submissions')
    else:
        form = AdminReviewForm()

    context = {
        'submission': submission,
        'form': form,
    }
    return render(request, 'events/admin_review_submission_detail.html', context)


@login_required
def create_deadline_event(request):
    """Admin creates deadline event with submission requirements"""
    if request.user.role != 'admin':
        messages.error(request, "Only administrators can create deadline events")
        return redirect('events:event_list')

    if request.method == 'POST':
        form = EventDeadlineForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.organizer = request.user
            event.event_type = 'deadline'
            event.save()
            form.save_m2m()

            # Notify participants
            if event.participants.exists():
                Notification.create_for_event(
                    event,
                    event.participants.all(),
                    notification_type='event_update',
                    title=f"New Deadline: {event.title}",
                    message=f"Deadline event '{event.title}' created. Due: {event.end_datetime.strftime('%B %d, %Y at %I:%M %p')}"
                )

            messages.success(request, f"Deadline event '{event.title}' created successfully!")
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventDeadlineForm()

    context = {
        'form': form,
        'title': 'Create Deadline Event with Submission Requirements',
    }
    return render(request, 'events/deadline_event_form.html', context)

@login_required
def get_system_notifications(request):
    """AJAX endpoint for system notifications"""
    notifications = request.user.notifications.filter(is_read=False)[:10]
    
    notifications_data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'link': n.link_url or '#',
        'created_at': n.created_at.isoformat()
    } for n in notifications]
    
    return JsonResponse({
        'unread_count': request.user.notifications.filter(is_read=False).count(),
        'notifications': notifications_data
    })

@login_required
def schedule_group_meeting(request, group_id=None):
    """Supervisor schedules a meeting for their group"""
    if request.user.role != 'supervisor':
        messages.error(request, "Only supervisors can schedule group meetings")
        return redirect('events:event_list')
    
    from groups.models import Group
    from datetime import datetime, time, timedelta
    
    # Get today's date and default time (2 PM)
    today = timezone.now().date()
    default_time = time(14, 0)  # 2:00 PM
    
    # If group_id is provided, use that group
    if group_id:
        group = get_object_or_404(Group, pk=group_id, supervisor=request.user)
        
        # Get active students for display
        group_memberships = group.members.filter(is_active=True).select_related('student')
        students = [membership.student for membership in group_memberships]
        
        if request.method == 'POST':
            # Get form data
            title = request.POST.get('title')
            date_str = request.POST.get('date')
            time_str = request.POST.get('time')
            duration = int(request.POST.get('duration', 60))
            location = request.POST.get('location', '')
            virtual_link = request.POST.get('virtual_link', '')
            description = request.POST.get('description', '')
            
            # Validate required fields
            if not all([title, date_str, time_str]):
                messages.error(request, "Please fill in all required fields")
                return render(request, 'events/schedule_meeting.html', {
                    'group': group,
                    'students': students,
                    'today': today,
                    'default_time': default_time.strftime('%H:%M')
                })
            
            # Combine date and time
            try:
                start_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                start_datetime = timezone.make_aware(start_datetime)
                end_datetime = start_datetime + timedelta(minutes=duration)
            except ValueError:
                messages.error(request, "Invalid date or time format")
                return render(request, 'events/schedule_meeting.html', {
                    'group': group,
                    'students': students,
                    'today': today,
                    'default_time': default_time.strftime('%H:%M')
                })
            
            # CHECK: Ensure only one event per day
            existing_event = Event.objects.filter(
                is_active=True,
                is_cancelled=False,
                start_datetime__date=start_datetime.date()
            ).first()
            
            if existing_event:
                messages.error(
                    request, 
                    f"Cannot schedule event. There's already an event on {start_datetime.date()}: "
                    f"'{existing_event.title}' at {existing_event.start_datetime.time()}"
                )
                return render(request, 'events/schedule_meeting.html', {
                    'group': group,
                    'students': students,
                    'today': today,
                    'default_time': default_time.strftime('%H:%M'),
                    'error_date': date_str
                })
            
            # Create the event
            event = Event.objects.create(
                title=title,
                description=description,
                event_type='meeting',
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location=location,
                virtual_link=virtual_link,
                group=group,
                organizer=request.user,
                created_by=request.user,
                priority='medium'
            )
            
            # Add all group students as participants
            if students:
                event.participants.set(students)
                
                # Create attendance records
                for student in students:
                    EventAttendance.objects.create(
                        event=event,
                        user=student,
                        status='pending'
                    )
                
                # Send notifications
                Notification.create_for_event(
                    event,
                    students,
                    notification_type='event_update',
                    title=f"Group Meeting Scheduled: {event.title}",
                    message=f"Your supervisor {request.user.display_name} scheduled a group meeting on {event.start_datetime.strftime('%B %d, %Y at %I:%M %p')}"
                )
            else:
                messages.warning(request, "Group has no active students to invite")
            
            messages.success(request, f"Group meeting '{event.title}' scheduled successfully!")
            return redirect('events:event_detail', pk=event.pk)
        
        # GET request - render form
        return render(request, 'events/schedule_meeting.html', {
            'group': group,
            'students': students,
            'today': today,
            'default_time': default_time.strftime('%H:%M')
        })
    
    # No group_id provided - show group selection
    groups = Group.objects.filter(supervisor=request.user, is_active=True)
    if not groups.exists():
        messages.error(request, "You don't supervise any active groups")
        return redirect('events:event_list')
    
    # If only one group, redirect to that group's scheduling page
    if groups.count() == 1:
        return redirect('events:schedule_group_meeting_for_group', group_id=groups.first().pk)
    
    # Show group selection
    return render(request, 'events/schedule_meeting.html', {
        'groups': groups,
        'today': today,
        'default_time': default_time.strftime('%H:%M')
    })
@login_required
def check_date_availability(request, date_str):
    """API endpoint to check if date has an event"""
    try:
        from datetime import datetime
        check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        existing_event = Event.objects.filter(
            is_active=True,
            is_cancelled=False,
            start_datetime__date=check_date
        ).first()
        
        if existing_event:
            return JsonResponse({
                'exists': True,
                'event_title': existing_event.title,
                'event_time': existing_event.start_datetime.strftime("%I:%M %p"),
            })
        else:
            return JsonResponse({'exists': False})
            
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)