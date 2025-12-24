# File: chat/management/commands/dissolve_chat_rooms.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import ChatRoom, ChatRoomMember, Message, ChatNotification, PendingMessage
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Dissolve (delete) chat rooms based on various criteria'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--room-type',
            type=str,
            help='Filter by room type: group, direct, supervisor'
        )
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Only delete inactive rooms'
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=0,
            help='Delete rooms older than X days'
        )
        parser.add_argument(
            '--empty-only',
            action='store_true',
            help='Only delete empty rooms (no messages)'
        )
        parser.add_argument(
            '--room-ids',
            type=str,
            help='Comma-separated list of specific room IDs to delete'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        queryset = ChatRoom.objects.all()
        
        # Apply filters
        if options['room_type']:
            queryset = queryset.filter(room_type=options['room_type'])
            self.stdout.write(f"Filtering by room type: {options['room_type']}")
        
        if options['inactive_only']:
            queryset = queryset.filter(is_active=False)
            self.stdout.write("Filtering inactive rooms only")
        
        if options['older_than'] > 0:
            cutoff_date = timezone.now() - timezone.timedelta(days=options['older_than'])
            queryset = queryset.filter(created_at__lt=cutoff_date)
            self.stdout.write(f"Filtering rooms older than {options['older_than']} days")
        
        if options['empty_only']:
            from django.db.models import Count
            queryset = queryset.annotate(message_count=Count('messages')).filter(message_count=0)
            self.stdout.write("Filtering empty rooms only")
        
        if options['room_ids']:
            room_ids = [int(id.strip()) for id in options['room_ids'].split(',')]
            queryset = queryset.filter(id__in=room_ids)
            self.stdout.write(f"Filtering specific room IDs: {room_ids}")
        
        room_count = queryset.count()
        
        if room_count == 0:
            self.stdout.write(self.style.WARNING("No rooms found matching criteria"))
            return
        
        self.stdout.write(f"\nFound {room_count} room(s) to dissolve:")
        for room in queryset:
            msg_count = room.messages.count()
            member_count = room.participants.count()
            self.stdout.write(f"  • {room.name} (ID: {room.id}, Type: {room.room_type}, Messages: {msg_count}, Members: {member_count})")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\nDRY RUN: No rooms were actually deleted"))
            return
        
        # Confirm deletion
        confirm = input(f"\nAre you sure you want to dissolve {room_count} chat room(s)? (yes/NO): ")
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING("Operation cancelled"))
            return
        
        # Delete rooms
        deleted_count = 0
        with transaction.atomic():
            for room in queryset:
                try:
                    # Clean up related objects first
                    ChatNotification.objects.filter(room=room).delete()
                    PendingMessage.objects.filter(room=room).delete()
                    ChatRoomMember.objects.filter(room=room).delete()
                    Message.objects.filter(room=room).delete()
                    
                    # Delete the room
                    room_name = room.name
                    room_id = room.id
                    room.delete()
                    
                    deleted_count += 1
                    self.stdout.write(f"✓ Dissolved room: {room_name} (ID: {room_id})")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Failed to dissolve room {room.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully dissolved {deleted_count}/{room_count} chat room(s)"))