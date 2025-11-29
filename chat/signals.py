# File: chat/signals.py

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from groups.models import Group, GroupMembership
from .models import ChatRoom, ChatRoomMember


@receiver(post_save, sender=Group)
def create_group_chat_room(sender, instance, created, **kwargs):
    """
    Automatically create a chat room when a new group is created
    """
    if created:
        # Create chat room for the group
        room = ChatRoom.objects.create(
            name=f"{instance.name} - Group Chat",
            room_type='supervisor',  # Use supervisor type for managed groups
            group=instance,
            is_active=True,
            is_frozen=True,  # Groups are time-restricted by default
            schedule_start_time=instance.supervisor.profile.schedule_start_time if hasattr(instance.supervisor, 'profile') else None,
            schedule_end_time=instance.supervisor.profile.schedule_end_time if hasattr(instance.supervisor, 'profile') else None,
            schedule_days=getattr(instance.supervisor.profile, 'schedule_days', None) if hasattr(instance.supervisor, 'profile') else None
        )
        
        # Add supervisor to the room
        room.participants.add(instance.supervisor)
        ChatRoomMember.objects.create(
            room=room,
            user=instance.supervisor,
            notifications_enabled=True
        )


@receiver(post_save, sender=GroupMembership)
def add_student_to_group_chat(sender, instance, created, **kwargs):
    """
    Automatically add students to group chat when they join a group
    """
    if created and instance.is_active:
        # Find the group's chat room
        try:
            room = ChatRoom.objects.get(group=instance.group, is_active=True)
            
            # Add student to the room
            if not room.participants.filter(id=instance.student.id).exists():
                room.participants.add(instance.student)
                
                # Create ChatRoomMember
                ChatRoomMember.objects.get_or_create(
                    room=room,
                    user=instance.student,
                    defaults={'notifications_enabled': True}
                )
                
                # Send system message
                from .models import Message
                Message.objects.create(
                    room=room,
                    sender=instance.student,
                    message_type='system',
                    content=f"{instance.student.display_name} joined the group"
                )
        except ChatRoom.DoesNotExist:
            # If room doesn't exist, create it
            room = ChatRoom.objects.create(
                name=f"{instance.group.name} - Group Chat",
                room_type='supervisor',
                group=instance.group,
                is_active=True,
                is_frozen=True
            )
            room.participants.add(instance.group.supervisor, instance.student)
            ChatRoomMember.objects.create(room=room, user=instance.group.supervisor)
            ChatRoomMember.objects.create(room=room, user=instance.student)


@receiver(post_save, sender=GroupMembership)
def handle_student_removal(sender, instance, **kwargs):
    """
    Handle student removal from group chat when they leave the group
    """
    if not instance.is_active:
        try:
            room = ChatRoom.objects.get(group=instance.group, is_active=True)
            
            # Remove from participants
            room.participants.remove(instance.student)
            
            # Deactivate membership
            try:
                member = ChatRoomMember.objects.get(room=room, user=instance.student)
                member.is_active = False
                member.save()
            except ChatRoomMember.DoesNotExist:
                pass
            
            # Send system message
            from .models import Message
            Message.objects.create(
                room=room,
                sender=instance.student,
                message_type='system',
                content=f"{instance.student.display_name} left the group"
            )
        except ChatRoom.DoesNotExist:
            pass