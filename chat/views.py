# File: Desktop/Prime/chat/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max, F, Avg, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
import json

from .models import ChatRoom, Message, ChatRoomMember, ChatNotification
from .forms import CreateChatRoomForm
from accounts.models import User
from groups.models import Group
from analytics.models import StressLevel
from analytics.sentiment import AdvancedSentimentAnalyzer


@login_required
def chat_home(request):
    """Enhanced chat home page with analytics"""
    
    # Get user's chat rooms with enhanced data
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants', 'members')
    
    room_data = []
    total_unread = 0
    active_rooms = 0
    
    for room in rooms:
        # Get last message
        last_message = room.messages.filter(is_deleted=False).order_by('-timestamp').first()
        
        # Calculate unread count
        try:
            member = room.members.get(user=request.user)
            unread = room.messages.filter(
                timestamp__gt=member.last_read_at,
                is_deleted=False
            ).exclude(sender=request.user).count()
        except ChatRoomMember.DoesNotExist:
            unread = 0
        
        total_unread += unread
        
        # Get online count
        online_count = room.members.filter(is_online=True).count()
        
        # Get participant count
        participant_count = room.participants.count()
        
        # Check accessibility
        is_accessible = room.is_accessible_now()
        
        if is_accessible and last_message and (timezone.now() - last_message.timestamp).days < 1:
            active_rooms += 1
        
        # Calculate average sentiment (last 10 messages)
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
            'avg_sentiment': avg_sentiment
        })
    
    # Sort by last message time
    room_data.sort(key=lambda x: x['room'].last_message_at or timezone.now(), reverse=True)
    
    context = {
        'room_data': room_data,
        'total_unread': total_unread,
        'active_rooms': active_rooms,
        'title': 'Chat - PrimeTime'
    }
    
    return render(request, 'chat/chat_home.html', context)


@login_required
def chat_room(request, room_id):
    """Enhanced chat room view with sentiment analysis"""
    
    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)
    
    # Check access
    if not room.participants.filter(pk=request.user.pk).exists():
        messages.error(request, "You don't have access to this chat room")
        return redirect('chat:chat_home')
    
    # Check if room is accessible at current time
    if not room.is_accessible_now():
        schedule_info = ""
        if room.schedule_start_time and room.schedule_end_time:
            schedule_info = f"This room is accessible from {room.schedule_start_time.strftime('%I:%M %p')} to {room.schedule_end_time.strftime('%I:%M %p')}"
            if room.schedule_days:
                schedule_info += f" on {room.schedule_days}"
        
        messages.warning(request, f'This chat room is currently frozen. {schedule_info}')
        return redirect('chat:chat_home')
    
    # Get or create member
    member, created = ChatRoomMember.objects.get_or_create(
        room=room,
        user=request.user
    )
    
    # Get messages with sentiment data
    messages_qs = room.messages.filter(
        is_deleted=False
    ).select_related(
        'sender', 'sender__profile', 'reply_to'
    ).prefetch_related('reactions').order_by('timestamp')
    
    # Mark as read
    member.mark_as_read()
    
    # Update last seen
    member.update_last_seen()
    
    # Get participants with profile data
    participants = room.participants.select_related('profile').all()
    
    # Calculate date groupings for messages
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    context = {
        'room': room,
        'messages': messages_qs,
        'participants': participants,
        'member': member,
        'today': today,
        'yesterday': yesterday,
        'title': room.name
    }
    
    return render(request, 'chat/room.html', context)


@login_required
def create_room(request):
    """Create a new chat room (admin/supervisor only)"""
    
    if request.user.role not in ['admin', 'supervisor']:
        messages.error(request, 'Only admins and supervisors can create chat rooms')
        return redirect('chat:chat_home')
    
    if request.method == 'POST':
        form = CreateChatRoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            
            # Add creator to participants if not already
            if not room.participants.filter(pk=request.user.pk).exists():
                room.participants.add(request.user)
            
            # Create ChatRoomMember for all participants
            for participant in room.participants.all():
                ChatRoomMember.objects.get_or_create(
                    room=room,
                    user=participant
                )
            
            # Send notifications to all participants
            for participant in room.participants.exclude(pk=request.user.pk):
                ChatNotification.objects.create(
                    user=participant,
                    notification_type='room_created',
                    room=room
                )
            
            messages.success(request, f'Chat room "{room.name}" created successfully!')
            return redirect('chat:chat_room', room_id=room.pk)
    else:
        form = CreateChatRoomForm()
        
        # Filter participants based on role
        if request.user.is_supervisor:
            # Supervisors can add their group members
            supervised_groups = Group.objects.filter(supervisor=request.user)
            supervised_students = User.objects.filter(
                student_memberships__group__in=supervised_groups,
                is_active=True
            ).distinct()
            form.fields['participants'].queryset = supervised_students
    
    context = {
        'form': form,
        'title': 'Create Chat Room - PrimeTime'
    }
    return render(request, 'chat/create_room.html', context)


@login_required
def chat_notifications(request):
    """View chat notifications"""
    
    notifications = request.user.chat_notifications.select_related(
        'room', 'message', 'message__sender'
    ).order_by('-created_at')[:50]
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        messages.success(request, 'All notifications marked as read')
        return redirect('chat:notifications')
    
    # Calculate stats
    unread_count = notifications.filter(is_read=False).count()
    
    week_ago = timezone.now() - timedelta(days=7)
    week_count = notifications.filter(created_at__gte=week_ago).count()
    
    mention_count = notifications.filter(notification_type='mention').count()
    reply_count = notifications.filter(notification_type='reply').count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'week_count': week_count,
        'mention_count': mention_count,
        'reply_count': reply_count,
        'title': 'Notifications - PrimeTime'
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


# AJAX views
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
def get_unread_counts(request):
    """Get unread message counts for all rooms (AJAX)"""
    
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    unread_data = {}
    total_unread = 0
    
    for room in rooms:
        try:
            member = room.members.get(user=request.user)
            unread = room.messages.filter(
                timestamp__gt=member.last_read_at,
                is_deleted=False
            ).exclude(sender=request.user).count()
            
            unread_data[room.id] = unread
            total_unread += unread
        except ChatRoomMember.DoesNotExist:
            unread_data[room.id] = 0
    
    return JsonResponse({
        'total_unread': total_unread,
        'rooms': unread_data
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
    
    return JsonResponse({
        'student': student.display_name,
        'stress_level': stress_analysis.level,
        'chat_sentiment': stress_analysis.chat_sentiment_score,
        'deadline_pressure': stress_analysis.deadline_pressure,
        'workload': stress_analysis.workload_score,
        'social_isolation': stress_analysis.social_isolation_score,
        'calculated_at': stress_analysis.calculated_at.isoformat()
    })