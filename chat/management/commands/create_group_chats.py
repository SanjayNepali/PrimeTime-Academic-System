# File: chat/management/commands/create_group_chats.py
# Save this EXACTLY as shown

from django.core.management.base import BaseCommand
from groups.models import Group, GroupMembership
from chat.models import ChatRoom, ChatRoomMember, Message
from django.db import transaction


class Command(BaseCommand):
    help = 'Creates chat rooms for existing groups'

    def handle(self, *args, **options):
        self.stdout.write('Creating group chats...\n')
        
        groups = Group.objects.filter(is_active=True)
        created = 0
        skipped = 0
        
        for group in groups:
            # Check if room exists
            if ChatRoom.objects.filter(group=group).exists():
                self.stdout.write(f'  ⏭️  Skipping {group.name} (already exists)')
                skipped += 1
                continue
            
            try:
                with transaction.atomic():
                    # Create room
                    room = ChatRoom.objects.create(
                        name=f"{group.name} - Group Chat",
                        room_type='supervisor',
                        group=group,
                        is_active=True,
                        is_frozen=True,
                        created_by=group.created_by
                    )
                    
                    # Add supervisor
                    room.participants.add(group.supervisor)
                    ChatRoomMember.objects.create(
                        room=room,
                        user=group.supervisor,
                        notifications_enabled=True
                    )
                    
                    # Add students
                    members = GroupMembership.objects.filter(
                        group=group,
                        is_active=True
                    )
                    
                    for membership in members:
                        room.participants.add(membership.student)
                        ChatRoomMember.objects.create(
                            room=room,
                            user=membership.student,
                            notifications_enabled=True
                        )
                    
                    # Welcome message
                    Message.objects.create(
                        room=room,
                        sender=group.supervisor,
                        message_type='system',
                        content=f"Welcome to {group.name} group chat!"
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ Created: {room.name} ({members.count()} students)'
                        )
                    )
                    created += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error for {group.name}: {str(e)}')
                )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Total: {groups.count()}')
        self.stdout.write(self.style.SUCCESS(f'Created: {created}'))
        self.stdout.write(f'Skipped: {skipped}')