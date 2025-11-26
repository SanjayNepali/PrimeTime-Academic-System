# ========================================
# File: Desktop/Prime/chat/views.py
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max, F

from .models import ChatRoom, Message, ChatRoomMember, ChatNotification
from .forms import CreateChatRoomForm
from accounts.models import User
from groups.models import Group


@login_required
def chat_home(request):
    """Chat home page - list of accessible rooms"""
    
    # Get user's chat rooms
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).annotate(
        last_msg_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(messages__timestamp__gt=request.user.chat_memberships__last_read_at) & ~Q(messages__sender=request.user))
    ).order_by('-last_msg_time')
    
    context = {
        'rooms': rooms,
        'title': 'Chat - PrimeTime'
    }
    return render(request, 'chat/chat_home.html', context)


@login_required
def chat_room(request, room_id):
    """Chat room view"""
    
    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)
    
    # Check access
    if not room.participants.filter(pk=request.user.pk).exists():
        messages.error(request, "You don't have access to this chat room")
        return redirect('chat:chat_home')
    
    # Check if room is accessible at current time
    if not room.is_accessible_now():
        messages.warning(request, 'This chat room is currently frozen by the supervisor')
        return redirect('chat:chat_home')
    
    # Get or create member
    member, created = ChatRoomMember.objects.get_or_create(
        room=room,
        user=request.user
    )
    
    # Get messages
    messages_qs = room.messages.filter(is_deleted=False).select_related(
        'sender', 'reply_to'
    ).prefetch_related('reactions').order_by('timestamp')
    
    # Mark as read
    member.mark_as_read()
    
    # Get participants
    participants = room.participants.all()
    
    context = {
        'room': room,
        'messages': messages_qs,
        'participants': participants,
        'member': member,
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
            messages.success(request, f'Chat room "{room.name}" created successfully!')
            return redirect('chat:chat_room', room_id=room.pk)
    else:
        form = CreateChatRoomForm()
    
    return render(request, 'chat/create_room.html', {'form': form})


@login_required
def chat_notifications(request):
    """View chat notifications"""
    
    notifications = request.user.chat_notifications.all()[:50]
    
    if request.GET.get('mark_all_read'):
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read')
        return redirect('chat:notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count()
    }
    return render(request, 'chat/notifications.html', context)


# AJAX views
@login_required
def get_room_messages(request, room_id):
    """Get messages for a room (AJAX)"""
    
    room = get_object_or_404(ChatRoom, pk=room_id)
    
    if not room.participants.filter(pk=request.user.pk).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    messages_qs = room.messages.filter(is_deleted=False).select_related('sender').order_by('-timestamp')[:50]
    
    messages_data = [{
        'id': msg.id,
        'sender_id': msg.sender.id,
        'sender_name': msg.sender.display_name,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'sentiment_score': msg.sentiment_score
    } for msg in messages_qs]
    
    return JsonResponse({'messages': list(reversed(messages_data))})