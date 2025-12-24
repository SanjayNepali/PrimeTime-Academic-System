# File: Desktop/Prime/chat/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max, F, Avg, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta, datetime, time as datetime_time
import json
from .forms import CreateChatRoomForm, UpdateChatRoomForm
from .models import ChatRoom, Message, ChatRoomMember, ChatNotification
from .forms import CreateChatRoomForm
from accounts.models import User
from groups.models import Group
from analytics.models import StressLevel
from analytics.sentiment import AdvancedSentimentAnalyzer


# ============================================
# UPDATED: CHECK USER AVAILABILITY
# ============================================
def check_user_availability(user, current_user):
    """
    Check if a user is available for messaging based on time restrictions
    Returns (is_available: bool, restriction_msg: str)
    """
    # Supervisors and admins can message anytime
    if current_user.role in ['supervisor', 'admin']:
        return True, None
    
    # If messaging a supervisor, check SUPERVISOR's schedule
    if user.role == 'supervisor':
        if not user.schedule_enabled:
            return True, None
        
        if not user.is_available_now():
            return False, user.get_availability_message()
        
        return True, None
    
    # Students messaging students - no restrictions
    return True, None


@login_required
def chat_home(request):
    """Enhanced chat home with groups and direct messages separated"""
    
    # Get user's chat rooms
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants', 'members').order_by('-last_message_at')
    
    room_data = []
    total_unread = 0
    group_unread = 0
    direct_unread = 0
    
    # Counters for room types
    group_rooms_count = 0
    direct_rooms_count = 0
    
    for room in rooms:
        # Get last message
        last_message = room.messages.filter(is_deleted=False).order_by('-timestamp').first()
        
        # Calculate ACCURATE unread count
        try:
            member = room.members.get(user=request.user)
            unread = room.messages.filter(
                timestamp__gt=member.last_read_at,
                is_deleted=False
            ).exclude(sender=request.user).count()
        except ChatRoomMember.DoesNotExist:
            unread = room.messages.filter(
                is_deleted=False
            ).exclude(sender=request.user).count()
        
        total_unread += unread
        
        # Track group vs direct unread AND count room types
        if room.room_type == 'direct':
            direct_unread += unread
            direct_rooms_count += 1
        else:
            group_unread += unread
            group_rooms_count += 1
        
        # Get online count
        online_count = room.members.filter(is_online=True).count()
        
        # Get participant count
        participant_count = room.participants.count()
        
        # ============================================
        # UPDATED: CHECK ACCESSIBILITY WITH SUPERVISOR SCHEDULE
        # ============================================
        is_accessible = True
        restriction_msg = None
        
        if room.room_type == 'supervisor' or room.group:
            # Group chat - check supervisor's schedule
            if room.group and room.group.supervisor:
                supervisor = room.group.supervisor
                if supervisor.schedule_enabled and not supervisor.is_available_now():
                    is_accessible = True  # Chat is accessible but messages will be pending
                    restriction_msg = supervisor.get_availability_message()
        
        elif room.room_type == 'direct':
            # Direct message - check recipient's schedule
            other_user = room.participants.exclude(id=request.user.id).first()
            if other_user and other_user.role == 'supervisor':
                is_available, msg = check_user_availability(other_user, request.user)
                is_accessible = True  # Chat is accessible but messages will be pending
                restriction_msg = msg if not is_available else None
        
        # Calculate average sentiment
        recent_messages = room.messages.filter(
            is_deleted=False
        ).order_by('-timestamp')[:10]
        
        avg_sentiment = None
        if recent_messages.exists():
            sentiment_sum = sum(msg.sentiment_score for msg in recent_messages)
            avg_sentiment = sentiment_sum / len(recent_messages)
        
        room_data.append({
            'room': room,
            'last_message': last_message,
            'unread': unread,
            'online_count': online_count,
            'participant_count': participant_count,
            'is_accessible': is_accessible,
            'restriction_msg': restriction_msg,
            'avg_sentiment': avg_sentiment
        })
    
    # Separate direct messages for the template
    direct_messages = [r for r in room_data if r['room'].room_type == 'direct']
    group_messages = [r for r in room_data if r['room'].room_type != 'direct']
    
    context = {
        'room_data': room_data,
        'direct_messages': direct_messages,
        'group_messages': group_messages,
        'total_unread': total_unread,
        'group_unread': group_unread,
        'direct_unread': direct_unread,
        'group_rooms_count': group_rooms_count,
        'direct_rooms_count': direct_rooms_count,
        'title': 'Chat - PrimeTime'
    }
    
    return render(request, 'chat/chat_home.html', context)


@login_required
def search_users(request):
    """AJAX endpoint to search for users to message"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search users (exclude self)
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(email__icontains=query) |
        Q(full_name__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query),
        is_active=True,
        is_enabled=True
    ).exclude(id=request.user.id)[:20]
    
    # Build results with availability info
    results = []
    for user in users:
        is_available, restriction_msg = check_user_availability(user, request.user)
        
        results.append({
            'id': user.id,
            'name': user.display_name,
            'initials': f"{user.first_name[0] if user.first_name else user.username[0]}{user.last_name[0] if user.last_name else ''}".upper(),
            'role': user.get_role_display(),
            'department': user.department or '',
            'time_restricted': not is_available,
            'restriction_msg': restriction_msg
        })
    
    return JsonResponse({'users': results})


@login_required
def user_chat(request, user_id):
    """Start or continue a direct chat with a user"""
    other_user = get_object_or_404(User, pk=user_id, is_active=True)
    
    # Don't allow chatting with yourself
    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself")
        return redirect('chat:chat_home')
    
    # ============================================
    # UPDATED: CHECK SUPERVISOR AVAILABILITY
    # ============================================
    if other_user.role == 'supervisor':
        is_available, restriction_msg = check_user_availability(other_user, request.user)
        
        if not is_available and request.user.role == 'student':
            messages.info(request, f"{other_user.display_name} is not available right now. Your messages will be delivered when they're available. {restriction_msg}")
        elif not is_available and request.user.role == 'supervisor':
            messages.warning(request, f"Note: {other_user.display_name} is currently unavailable. Your messages will be delivered when they're available.")
    
    # Find or create direct message room
    existing_room = ChatRoom.objects.filter(
        room_type='direct',
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_room:
        return redirect('chat:chat_room', room_id=existing_room.id)
    
    # Create new direct message room
    room = ChatRoom.objects.create(
        name=f"{request.user.display_name} & {other_user.display_name}",
        room_type='direct',
        is_active=True
    )
    room.participants.add(request.user, other_user)
    
    # Create ChatRoomMember records
    ChatRoomMember.objects.create(room=room, user=request.user)
    ChatRoomMember.objects.create(room=room, user=other_user)
    
    messages.success(request, f'Started chat with {other_user.display_name}')
    return redirect('chat:chat_room', room_id=room.id)


@login_required
def chat_room(request, room_id):
    """Enhanced chat room view with proper read tracking and schedule checks"""
    
    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)
    
    # Check access
    if not room.participants.filter(pk=request.user.pk).exists():
        messages.error(request, "You don't have access to this chat room")
        return redirect('chat:chat_home')
    
    # ============================================
    # FIXED: CHAT IS ALWAYS ACCESSIBLE, PENDING MESSAGES HANDLED IN WEBSOCKET
    # ============================================
    is_accessible = True  # ALWAYS TRUE - Pending messages handled in WebSocket
    restriction_msg = None
    
    if room.room_type == 'supervisor' or room.group:
        # Group chat - check supervisor's schedule
        if room.group and room.group.supervisor:
            supervisor = room.group.supervisor
            if supervisor.schedule_enabled:
                if not supervisor.is_available_now():
                    restriction_msg = supervisor.get_availability_message()
                    
                    # Inform students about pending messages
                    if request.user.role == 'student':
                        messages.info(request, f"Supervisor is currently unavailable. Your messages will be delivered when they're available. {restriction_msg}")
    
    elif room.room_type == 'direct':
        # Direct message - check recipient's schedule
        other_user = room.participants.exclude(id=request.user.id).first()
        if other_user and other_user.role == 'supervisor':
            is_available, msg = check_user_availability(other_user, request.user)
            
            if not is_available and request.user.role == 'student':
                restriction_msg = msg
                messages.info(request, f"Supervisor is currently unavailable. Your messages will be delivered when they're available. {restriction_msg}")
    
    # Get or create member
    member, created = ChatRoomMember.objects.get_or_create(
        room=room,
        user=request.user
    )
    
    # Mark ALL existing messages as read when user views the room
    member.last_read_at = timezone.now()
    member.save(update_fields=['last_read_at'])
    
    # Update last seen
    member.update_last_seen()
    
    # Get messages
    messages_qs = room.messages.filter(
        is_deleted=False
    ).select_related(
        'sender', 'sender__profile', 'reply_to'
    ).prefetch_related('reactions').order_by('timestamp')
    
    # Get participants
    participants = room.participants.select_related('profile').all()
    
    # Check if room has any supervisor participants
    has_supervisor = room.participants.filter(role='supervisor').exists()
    
    # Date groupings
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    context = {
        'room': room,
        'messages': messages_qs,
        'participants': participants,
        'member': member,
        'today': today,
        'yesterday': yesterday,
        'is_accessible': is_accessible,  # ALWAYS TRUE
        'restriction_msg': restriction_msg,
        'has_supervisor': has_supervisor,
        'title': room.name
    }
    
    return render(request, 'chat/room.html', context)


@login_required
def get_unread_counts(request):
    """Get ACCURATE unread message counts for all rooms"""
    
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    unread_data = {}
    total_unread = 0
    
    for room in rooms:
        try:
            member = room.members.get(user=request.user)
            # Count only messages AFTER last_read_at from others
            unread = room.messages.filter(
                timestamp__gt=member.last_read_at,
                is_deleted=False
            ).exclude(sender=request.user).count()
            
            unread_data[room.id] = unread
            total_unread += unread
        except ChatRoomMember.DoesNotExist:
            # If no member record, count all non-self messages
            unread = room.messages.filter(
                is_deleted=False
            ).exclude(sender=request.user).count()
            unread_data[room.id] = unread
            total_unread += unread
    
    return JsonResponse({
        'total_unread': total_unread,
        'rooms': unread_data
    })


@login_required
def create_room(request):
    """Create a new chat room (admin/supervisor only)"""
    
    if request.user.role not in ['admin', 'supervisor']:
        messages.error(request, 'Only admins and supervisors can create chat rooms')
        return redirect('chat:chat_home')
    
    if request.method == 'POST':
        form = CreateChatRoomForm(request.POST, user=request.user)
        if form.is_valid():
            room = form.save()
            
            # Create ChatRoomMember for all participants
            from .models import ChatRoomMember
            for participant in room.participants.all():
                ChatRoomMember.objects.get_or_create(
                    room=room,
                    user=participant
                )
            
            # Send notifications to all participants
            from .models import ChatNotification
            for participant in room.participants.exclude(pk=request.user.pk):
                ChatNotification.objects.create(
                    user=participant,
                    notification_type='room_created',
                    room=room
                )
            
            messages.success(request, f'Chat room "{room.name}" created successfully!')
            return redirect('chat:chat_room', room_id=room.pk)
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CreateChatRoomForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Create Chat Room - PrimeTime'
    }
    return render(request, 'chat/create_room.html', context)


@login_required
def update_room(request, room_id):
    """Update chat room settings"""
    
    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)
    
    # Check permissions
    if not (request.user.role == 'admin' or 
            (request.user.role == 'supervisor' and room.room_type == 'supervisor' and 
             room.group and room.group.supervisor == request.user)):
        messages.error(request, "You don't have permission to edit this room")
        return redirect('chat:chat_room', room_id=room_id)
    
    if request.method == 'POST':
        form = UpdateChatRoomForm(request.POST, instance=room, user=request.user)
        if form.is_valid():
            updated_room = form.save()
            
            # Update ChatRoomMember records
            from .models import ChatRoomMember
            for participant in updated_room.participants.all():
                ChatRoomMember.objects.get_or_create(
                    room=updated_room,
                    user=participant
                )
            
            messages.success(request, f'Chat room "{updated_room.name}" updated successfully!')
            return redirect('chat:chat_room', room_id=updated_room.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UpdateChatRoomForm(instance=room, user=request.user)
    
    context = {
        'form': form,
        'room': room,
        'title': f'Update {room.name} - PrimeTime'
    }
    return render(request, 'chat/update_room.html', context)

@login_required
def chat_notifications(request):
    """View chat notifications"""
    
    # FIXED: Don't slice before filtering
    notifications_qs = request.user.chat_notifications.select_related(
        'room', 'message', 'message__sender'
    ).order_by('-created_at')
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications_qs.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        messages.success(request, 'All notifications marked as read')
        return redirect('chat:notifications')
    
    # NOW slice after filtering is done
    notifications = notifications_qs[:50]
    
    # Calculate stats
    unread_count = request.user.chat_notifications.filter(is_read=False).count()
    
    week_ago = timezone.now() - timedelta(days=7)
    week_count = request.user.chat_notifications.filter(created_at__gte=week_ago).count()
    
    mention_count = request.user.chat_notifications.filter(notification_type='mention').count()
    reply_count = request.user.chat_notifications.filter(notification_type='reply').count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'week_count': week_count,
        'mention_count': mention_count,
        'reply_count': reply_count,
        'title': 'Chat Notifications - PrimeTime'
    }
    
    return render(request, 'chat/notifications.html', context)

@login_required
def analytics_dashboard(request):
    """Analytics dashboard for supervisors/admins"""
    
    # Only supervisors and admins can access
    if request.user.role not in ['admin', 'supervisor']:
        messages.error(request, 'Access denied')
        return redirect('chat:chat_home')
    
    # Get relevant rooms based on role
    if request.user.is_admin:
        rooms = ChatRoom.objects.filter(is_active=True)
        students = User.objects.filter(role='student', is_enabled=True)
    else:
        # Supervisor sees their groups only
        supervised_groups = Group.objects.filter(supervisor=request.user)
        rooms = ChatRoom.objects.filter(
            group__in=supervised_groups,
            is_active=True
        )
        students = User.objects.filter(
            student_memberships__group__in=supervised_groups,
            is_active=True
        ).distinct()
    
    # Calculate sentiment statistics
    last_week = timezone.now() - timedelta(days=7)
    recent_messages = Message.objects.filter(
        room__in=rooms,
        timestamp__gte=last_week,
        is_deleted=False
    )
    
    total_messages = recent_messages.count()
    
    # Sentiment breakdown
    positive_messages = recent_messages.filter(sentiment_score__gt=0.3).count()
    negative_messages = recent_messages.filter(sentiment_score__lt=-0.3).count()
    neutral_messages = total_messages - positive_messages - negative_messages
    
    avg_sentiment = 0
    if total_messages > 0:
        sentiment_sum = sum(msg.sentiment_score for msg in recent_messages)
        avg_sentiment = (sentiment_sum / total_messages) * 100
        
        positive_percent = (positive_messages / total_messages) * 100
        negative_percent = (negative_messages / total_messages) * 100
        neutral_percent = (neutral_messages / total_messages) * 100
    else:
        positive_percent = negative_percent = neutral_percent = 0
    
    # Flagged content
    flagged_count = recent_messages.filter(is_flagged=True).count()
    
    # High stress students
    high_stress_students = StressLevel.objects.filter(
        student__in=students,
        level__gte=70
    ).select_related('student').order_by('-level', '-calculated_at')[:10]
    
    high_stress_count = high_stress_students.count()
    
    # Stress distribution
    stress_levels = StressLevel.objects.filter(
        student__in=students
    ).values_list('level', flat=True)
    
    low_stress = sum(1 for level in stress_levels if level < 40)
    medium_stress = sum(1 for level in stress_levels if 40 <= level < 70)
    high_stress_dist = sum(1 for level in stress_levels if level >= 70)
    
    stress_distribution = [low_stress, medium_stress, high_stress_dist]
    
    # Sentiment trend data (last 7 days)
    sentiment_dates = []
    positive_data = []
    negative_data = []
    
    for i in range(6, -1, -1):
        date = timezone.now() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0)
        date_end = date.replace(hour=23, minute=59, second=59)
        
        day_messages = recent_messages.filter(
            timestamp__gte=date_start,
            timestamp__lte=date_end
        )
        
        sentiment_dates.append(date.strftime('%a'))
        
        if day_messages.exists():
            pos_count = day_messages.filter(sentiment_score__gt=0.3).count()
            neg_count = day_messages.filter(sentiment_score__lt=-0.3).count()
            total_day = day_messages.count()
            
            positive_data.append((pos_count / total_day) * 100 if total_day > 0 else 0)
            negative_data.append((neg_count / total_day) * 100 if total_day > 0 else 0)
        else:
            positive_data.append(0)
            negative_data.append(0)
    
    # Activity data
    activity_labels = sentiment_dates
    activity_data = []
    
    for i in range(6, -1, -1):
        date = timezone.now() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0)
        date_end = date.replace(hour=23, minute=59, second=59)
        
        count = recent_messages.filter(
            timestamp__gte=date_start,
            timestamp__lte=date_end
        ).count()
        
        activity_data.append(count)
    
    # Most active rooms
    room_activity = []
    room_names = []
    
    for room in rooms.order_by('-last_message_at')[:5]:
        room_names.append(room.name)
        msg_count = room.messages.filter(
            timestamp__gte=last_week,
            is_deleted=False
        ).count()
        room_activity.append(msg_count)
    
    context = {
        'avg_sentiment': avg_sentiment,
        'high_stress_count': high_stress_count,
        'total_messages': total_messages,
        'flagged_count': flagged_count,
        'positive_percent': positive_percent,
        'negative_percent': negative_percent,
        'neutral_percent': neutral_percent,
        'high_stress_students': high_stress_students,
        'stress_distribution': json.dumps(stress_distribution),
        'sentiment_dates': json.dumps(sentiment_dates),
        'positive_data': json.dumps(positive_data),
        'negative_data': json.dumps(negative_data),
        'activity_labels': json.dumps(activity_labels),
        'activity_data': json.dumps(activity_data),
        'room_names': json.dumps(room_names),
        'room_activity': json.dumps(room_activity),
        'title': 'Analytics Dashboard - PrimeTime'
    }
    
    return render(request, 'chat/analytics_dashboard.html', context)


@login_required
def get_room_messages(request, room_id):
    """Get messages for a room (AJAX)"""
    
    room = get_object_or_404(ChatRoom, pk=room_id)
    
    if not room.participants.filter(pk=request.user.pk).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get messages with pagination
    page = request.GET.get('page', 1)
    messages_qs = room.messages.filter(
        is_deleted=False
    ).select_related('sender').order_by('-timestamp')
    
    paginator = Paginator(messages_qs, 50)
    messages_page = paginator.get_page(page)
    
    messages_data = [{
        'id': msg.id,
        'sender_id': msg.sender.id,
        'sender_name': msg.sender.display_name,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'sentiment_score': msg.sentiment_score,
        'is_flagged': msg.is_flagged
    } for msg in messages_page]
    
    return JsonResponse({
        'messages': list(reversed(messages_data)),
        'has_next': messages_page.has_next(),
        'has_previous': messages_page.has_previous()
    })


@login_required
def analyze_student_stress(request, student_id):
    """Analyze and return stress data for a specific student (AJAX)"""
    
    # Only supervisors and admins
    if request.user.role not in ['admin', 'supervisor']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    student = get_object_or_404(User, pk=student_id, role='student')
    
    # Run comprehensive analysis
    analyzer = AdvancedSentimentAnalyzer(student)
    stress_analysis = analyzer.comprehensive_stress_analysis(days=7)
    
    if not stress_analysis:
        return JsonResponse({
            'error': 'No stress data available',
            'student': student.display_name
        })
    
    return JsonResponse({
        'student': student.display_name,
        'stress_level': stress_analysis.level,
        'chat_sentiment': stress_analysis.chat_sentiment_score,
        'deadline_pressure': stress_analysis.deadline_pressure,
        'workload': stress_analysis.workload_score,
        'social_isolation': stress_analysis.social_isolation_score,
        'calculated_at': stress_analysis.calculated_at.isoformat()
    })


@login_required
def supervisor_chat(request, supervisor_id):
    """Direct chat with a supervisor"""
    
    supervisor = get_object_or_404(User, pk=supervisor_id, role='supervisor')
    
    # Check availability
    is_available, restriction_msg = check_user_availability(supervisor, request.user)
    
    # Supervisors get a notification but can still send
    if not is_available and request.user.role == 'supervisor':
        messages.warning(request, f"Note: {supervisor.display_name} will only see your messages during their available hours: {restriction_msg}")
    elif not is_available:
        messages.info(request, f"{supervisor.display_name} is not available right now. Your messages will be delivered when they're available. {restriction_msg}")
    
    # Find or create a direct message room between user and supervisor
    existing_room = ChatRoom.objects.filter(
        room_type='direct',
        participants=request.user
    ).filter(
        participants=supervisor
    ).first()
    
    if existing_room:
        return redirect('chat:chat_room', room_id=existing_room.id)
    
    # Create new direct message room
    room = ChatRoom.objects.create(
        name=f"Chat with {supervisor.display_name}",
        room_type='direct',
        is_active=True
    )
    room.participants.add(request.user, supervisor)
    
    # Create ChatRoomMember records
    ChatRoomMember.objects.create(room=room, user=request.user)
    ChatRoomMember.objects.create(room=room, user=supervisor)
    
    messages.success(request, f'Started chat with {supervisor.display_name}')
    return redirect('chat:chat_room', room_id=room.id)


@login_required
def project_forum(request, project_id):
    """Forum/discussion for a specific project"""
    
    from projects.models import Project
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has access to this project
    if not (request.user == project.student or 
            request.user == project.supervisor or 
            request.user.is_admin):
        messages.error(request, "You don't have access to this project's forum")
        return redirect('chat:chat_home')
    
    # Find or create project forum room
    existing_room = ChatRoom.objects.filter(
        room_type='group',
        group__isnull=True,  # Not associated with a group
        name__icontains=f"Project: {project.title}"
    ).first()
    
    if existing_room:
        return redirect('chat:chat_room', room_id=existing_room.id)
    
    # Create new project forum
    room = ChatRoom.objects.create(
        name=f"Project Forum: {project.title}",
        room_type='group',
        is_active=True
    )
    
    # Add relevant participants
    room.participants.add(project.student)
    if project.supervisor:
        room.participants.add(project.supervisor)
    
    # Create ChatRoomMember records
    ChatRoomMember.objects.create(room=room, user=project.student)
    if project.supervisor:
        ChatRoomMember.objects.create(room=room, user=project.supervisor)
    
    messages.success(request, f'Project forum created for {project.title}')
    return redirect('chat:chat_room', room_id=room.id)