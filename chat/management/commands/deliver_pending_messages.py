from django.core.management.base import BaseCommand
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from chat.models import PendingMessage, ChatRoom, Message
from accounts.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deliver ALL pending messages IMMEDIATELY - emergency bypass for time restrictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be delivered without actually delivering',
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Force deliver ALL pending messages regardless of supervisor availability',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force_all = options['force_all']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No messages will be delivered'))
        
        if force_all:
            self.stdout.write(self.style.WARNING('🔄 FORCE MODE - Will deliver ALL pending messages regardless of time restrictions'))
        else:
            self.stdout.write('🔄 Checking for pending messages...')
        
        # Get ALL pending messages regardless of availability
        if force_all:
            pending_messages = PendingMessage.objects.filter(
                status='pending'
            ).select_related('sender', 'target_supervisor', 'room')
            self.stdout.write(f'Found {pending_messages.count()} pending messages (FORCE ALL MODE)')
        else:
            # Get pending messages that are ready OR overdue for delivery
            pending_messages = PendingMessage.objects.filter(
                status='pending'
            ).select_related('sender', 'target_supervisor', 'room')
            self.stdout.write(f'Found {pending_messages.count()} total pending messages')
        
        delivered_count = 0
        expired_count = 0
        failed_count = 0
        bypassed_count = 0
        
        for pending_msg in pending_messages:
            # Check if expired
            if pending_msg.expires_at and timezone.now() > pending_msg.expires_at:
                if not dry_run:
                    pending_msg.mark_expired()
                    self.notify_expiry(pending_msg)
                expired_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⏰ Expired: Message from {pending_msg.sender.display_name} to {pending_msg.target_supervisor.display_name}'
                    )
                )
                continue
            
            # ============================================
            # FIX: FORCE DELIVERY - BYPASS ALL TIME CHECKS
            # ============================================
            if force_all or self.should_deliver_now(pending_msg):
                if not dry_run:
                    message = self.force_deliver_message(pending_msg)
                    
                    if message:
                        # Broadcast delivery via WebSocket
                        self.broadcast_message_delivery(pending_msg, message)
                        
                        # Notify sender
                        self.notify_sender(pending_msg, message)
                        
                        delivered_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ DELIVERED: Message #{pending_msg.id} from {pending_msg.sender.display_name} to {pending_msg.target_supervisor.display_name}'
                            )
                        )
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ❌ FAILED: Message #{pending_msg.id} - {pending_msg.error_message}'
                            )
                        )
                else:
                    if force_all:
                        self.stdout.write(
                            f'  📤 WOULD DELIVER (FORCE): Message from {pending_msg.sender.display_name} to {pending_msg.target_supervisor.display_name}'
                        )
                    else:
                        self.stdout.write(
                            f'  📤 WOULD DELIVER: Message from {pending_msg.sender.display_name} to {pending_msg.target_supervisor.display_name}'
                        )
                    delivered_count += 1
            else:
                # Message is still pending (not ready yet)
                bypassed_count += 1
                if pending_msg.scheduled_delivery_time:
                    time_until = pending_msg.scheduled_delivery_time - timezone.now()
                    hours = int(time_until.total_seconds() // 3600)
                    minutes = int((time_until.total_seconds() % 3600) // 60)
                    self.stdout.write(
                        f'  ⏳ STILL PENDING: Message #{pending_msg.id} - Will be delivered in {hours}h {minutes}m'
                    )
                else:
                    self.stdout.write(
                        f'  ⏳ STILL PENDING: Message #{pending_msg.id} - No delivery time scheduled'
                    )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ DELIVERED: {delivered_count} messages'))
        if bypassed_count > 0 and not force_all:
            self.stdout.write(self.style.WARNING(f'⏳ STILL PENDING: {bypassed_count} messages (waiting for supervisor availability)'))
        if expired_count > 0:
            self.stdout.write(self.style.WARNING(f'⏰ EXPIRED: {expired_count} messages'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ FAILED: {failed_count} messages'))
        
        if force_all:
            self.stdout.write(self.style.SUCCESS('🎯 FORCE MODE COMPLETE - All pending messages delivered!'))
        self.stdout.write('='*60)
    
    def should_deliver_now(self, pending_msg):
        """
        Check if message should be delivered NOW
        FIX: Only checks if supervisor exists, not their schedule
        """
        # If no supervisor target, deliver immediately
        if not pending_msg.target_supervisor:
            return True
        
        # If supervisor has no schedule enabled, deliver immediately
        if not pending_msg.target_supervisor.schedule_enabled:
            return True
        
        # If scheduled delivery time has passed, deliver immediately
        if pending_msg.scheduled_delivery_time and timezone.now() >= pending_msg.scheduled_delivery_time:
            return True
        
        # CRITICAL FIX: If supervisor exists and message is pending, deliver anyway
        # This bypasses the time restriction for emergency situations
        return True
    
    def force_deliver_message(self, pending_msg):
        """
        Force deliver a message regardless of supervisor availability
        """
        try:
            # Update room's last message time
            pending_msg.room.last_message_at = timezone.now()
            pending_msg.room.save(update_fields=['last_message_at'])
            
            # Create the actual message
            message = Message.objects.create(
                room=pending_msg.room,
                sender=pending_msg.sender,
                content=pending_msg.content,
                attachment=pending_msg.attachment,
                reply_to=pending_msg.reply_to,
                sentiment_score=pending_msg.sentiment_score,
                is_flagged=pending_msg.is_flagged,
                message_type='text'
            )
            
            # Update pending message status
            pending_msg.status = 'delivered'
            pending_msg.delivered_at = timezone.now()
            pending_msg.delivered_message = message
            pending_msg.save()
            
            logger.info(f'FORCE delivered pending message {pending_msg.id} as message {message.id}')
            return message
        
        except Exception as e:
            pending_msg.status = 'failed'
            pending_msg.error_message = str(e)
            pending_msg.attempts += 1
            pending_msg.last_attempt_at = timezone.now()
            pending_msg.save()
            logger.error(f'Error force delivering message {pending_msg.id}: {e}')
            return None
    
    def broadcast_message_delivery(self, pending_msg, message):
        """Broadcast delivered message to room via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            room_group_name = f'chat_{pending_msg.room.id}'
            
            # Send to all room participants
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'pending_message_delivered',
                    'pending_message_id': pending_msg.id,
                    'message_id': message.id,
                    'sender_id': message.sender.id,
                    'sender_name': message.sender.display_name,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'sentiment_score': message.sentiment_score,
                    'is_flagged': message.is_flagged,
                }
            )
            
            logger.info(f'Broadcasted delivery of pending message {pending_msg.id}')
        except Exception as e:
            logger.error(f'Error broadcasting message delivery: {e}')
    
    def notify_sender(self, pending_msg, message):
        """Notify sender that their pending message was delivered"""
        try:
            from events.models import Notification
            
            Notification.objects.create(
                recipient=pending_msg.sender,
                notification_type='chat',
                title='Message Delivered',
                message=f'Your message to {pending_msg.target_supervisor.display_name} has been delivered.',
                link_url=f'/chat/room/{pending_msg.room.id}/',
                priority='normal'
            )
            
            logger.info(f'Sent delivery notification to {pending_msg.sender.display_name}')
        except Exception as e:
            logger.error(f'Error sending notification: {e}')
    
    def notify_expiry(self, pending_msg):
        """Notify sender that their message expired"""
        try:
            from events.models import Notification
            
            Notification.objects.create(
                recipient=pending_msg.sender,
                notification_type='alert',
                title='Message Expired',
                message=f'Your message to {pending_msg.target_supervisor.display_name} was not delivered and has expired.',
                link_url=f'/chat/room/{pending_msg.room.id}/',
                priority='normal'
            )
            
            logger.info(f'Sent expiry notification to {pending_msg.sender.display_name}')
        except Exception as e:
            logger.error(f'Error sending expiry notification: {e}')