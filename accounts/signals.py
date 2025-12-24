# File: Desktop/Prime/accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=User)
def update_supervisor_chat_rooms(sender, instance, **kwargs):
    """
    Automatically update supervisor's chat room schedules when they change their profile settings
    """
    # Only process for supervisors
    if instance.role != 'supervisor':
        return
    
    # Import here to avoid circular imports
    from chat.models import ChatRoom
    
    # Get all supervisor chat rooms for this supervisor
    supervisor_rooms = ChatRoom.objects.filter(
        room_type='supervisor',
        group__supervisor=instance,
        is_frozen=True
    )
    
    # Update schedules for all frozen rooms
    for room in supervisor_rooms:
        if instance.schedule_enabled:
            # Update to supervisor's current schedule
            room.schedule_start_time = instance.schedule_start_time
            room.schedule_end_time = instance.schedule_end_time
            room.schedule_days = instance.schedule_days
            room.save(update_fields=['schedule_start_time', 'schedule_end_time', 'schedule_days'])
            print(f"✅ Updated schedule for room: {room.name}")
        else:
            # If supervisor disabled schedule, unfreeze the room
            room.is_frozen = False
            room.schedule_start_time = None
            room.schedule_end_time = None
            room.schedule_days = ''
            room.save(update_fields=['is_frozen', 'schedule_start_time', 'schedule_end_time', 'schedule_days'])
            print(f"✅ Unfroze room (schedule disabled): {room.name}")