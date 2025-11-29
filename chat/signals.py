# ============================================
# File: chat/signals.py (UPDATE THIS FILE)
# PURPOSE: Group chat automation + Real-time stress calculation
# ============================================

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

from groups.models import Group, GroupMembership
from .models import ChatRoom, ChatRoomMember, Message
from analytics.sentiment import AdvancedSentimentAnalyzer
from analytics.models import StressLevel

logger = logging.getLogger(__name__)


# ============================================
# EXISTING GROUP CHAT SIGNALS (Keep these)
# ============================================

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
            Message.objects.create(
                room=room,
                sender=instance.student,
                message_type='system',
                content=f"{instance.student.display_name} left the group"
            )
        except ChatRoom.DoesNotExist:
            pass


# ============================================
# NEW: REAL-TIME STRESS CALCULATION
# ============================================

@receiver(post_save, sender=Message)
def calculate_stress_on_message(sender, instance, created, **kwargs):
    """
    REAL-TIME STRESS CALCULATION
    Automatically calculate stress whenever a message is sent
    """
    if not created:
        return  # Only process new messages
    
    if instance.is_deleted:
        return  # Skip deleted messages
    
    if instance.message_type == 'system':
        return  # Skip system messages
    
    # Only calculate for student messages
    if instance.sender.role != 'student':
        logger.info(f"Skipping stress calculation for non-student: {instance.sender}")
        return
    
    logger.info(f"🧠 Calculating stress for {instance.sender.display_name} after new message")
    
    try:
        # Check if we recently calculated (avoid spam)
        recent_calculation = StressLevel.objects.filter(
            student=instance.sender,
            calculated_at__gte=timezone.now() - timedelta(minutes=5)
        ).exists()
        
        if recent_calculation:
            logger.info(f"⏭️ Skipping - stress calculated within last 5 minutes")
            return
        
        # Run comprehensive stress analysis
        analyzer = AdvancedSentimentAnalyzer(instance.sender)
        result = analyzer.comprehensive_stress_analysis(days=7)
        
        if result:
            logger.info(f"✅ Stress calculated: {result.level:.1f}% for {instance.sender.display_name}")
            
            # Alert if high stress detected
            if result.level >= 70:
                logger.warning(f"🚨 HIGH STRESS ALERT: {instance.sender.display_name} - {result.level:.1f}%")
                send_stress_alert(instance.sender, result)
        else:
            logger.info(f"⚠️ Insufficient data for stress calculation")
            
    except Exception as e:
        logger.error(f"❌ Error calculating stress: {e}")


def send_stress_alert(student, stress_result):
    """
    Send alert to supervisors AND broadcast via WebSocket for real-time updates
    """
    try:
        from events.models import Notification
        from groups.models import GroupMembership
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get student's supervisor
        membership = GroupMembership.objects.filter(
            student=student,
            is_active=True
        ).first()
        
        if membership and membership.group.supervisor:
            supervisor = membership.group.supervisor
            
            # Send notification to supervisor
            Notification.objects.create(
                recipient=supervisor,
                notification_type='alert',
                title='🚨 High Stress Student Detected',
                message=f"{student.display_name} shows stress level of {stress_result.level:.1f}%. "
                        f"Please check in with them.",
                link_url=f'/analytics/supervisor/student/{student.id}/',
                priority='high'
            )
            
            logger.info(f"📧 Stress alert sent to {supervisor.display_name}")
            
            # BROADCAST VIA WEBSOCKET FOR REAL-TIME UPDATE
            channel_layer = get_channel_layer()
            
            stress_data = {
                'type': 'stress_level_updated',
                'student_id': student.id,
                'student_name': student.display_name,
                'stress_level': float(stress_result.level),
                'stress_category': stress_result.stress_category,
                'chat_sentiment': float(stress_result.chat_sentiment_score),
                'deadline_pressure': float(stress_result.deadline_pressure),
                'workload': float(stress_result.workload_score),
                'social_isolation': float(stress_result.social_isolation_score),
                'timestamp': stress_result.calculated_at.isoformat()
            }
            
            # Send to student's own WebSocket
            async_to_sync(channel_layer.group_send)(
                f'stress_student_{student.id}',
                stress_data
            )
            
            # Send to supervisor's WebSocket
            async_to_sync(channel_layer.group_send)(
                f'stress_supervisor_{supervisor.id}',
                stress_data
            )
            
            # Send to admin WebSocket
            async_to_sync(channel_layer.group_send)(
                'stress_admin_all',
                stress_data
            )
            
            logger.info(f"📡 Real-time stress update broadcasted for {student.display_name}")
            
    except Exception as e:
        logger.error(f"❌ Error sending stress alert: {e}")