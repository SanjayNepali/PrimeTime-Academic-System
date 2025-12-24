# File: chat/consumers.py - COMPLETE WORKING VERSION

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
import traceback

from .models import ChatRoom, Message, ChatRoomMember, TypingIndicator, MessageReaction, PendingMessage
from accounts.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat with WORKING time restrictions"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.update_user_status(online=True)
        await self.accept()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.display_name,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.update_user_status(online=False)
        await self.remove_typing_indicator()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.display_name,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'reaction':
                await self.handle_reaction(data)
            elif message_type == 'delete':
                await self.handle_delete(data)
            elif message_type == "mark_room_read":
                await self.handle_mark_room_read(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            print(f"❌ WebSocket receive error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Server error occurred'
            }))
    
    async def handle_message(self, data):
        """
        FIXED: Handle new chat message with WORKING time restrictions
        """
        content = data.get('message', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return
        
        print(f"🔍 Message from {self.user.display_name} (role: {self.user.role})")
        
        # Check for inappropriate content FIRST
        try:
            analysis = await self.analyze_content(content)
        except Exception as e:
            print(f"❌ Content analysis error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Unable to analyze message content'
            }))
            return
        
        if analysis['is_inappropriate']:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Your message contains inappropriate content and cannot be sent.',
                'details': analysis['inappropriate_issues']
            }))
            return
        
        # ============================================
        # CHECK SUPERVISOR AVAILABILITY
        # ============================================
        availability_info = await self.check_supervisor_availability()
        
        print(f"📊 Availability check result:")
        print(f"   - Is available: {availability_info['is_available']}")
        print(f"   - Supervisor: {availability_info['supervisor']}")
        print(f"   - Message: {availability_info['message']}")
        
        # ============================================
        # CRITICAL FIX: Admins and supervisors can ALWAYS send
        # ============================================
        user_can_override = self.user.role in ['admin', 'supervisor']
        
        if availability_info['is_available'] or user_can_override:
            # DELIVER IMMEDIATELY
            print(f"✅ Delivering message immediately")
            
            message = await self.save_message(content, reply_to_id, analysis['sentiment_score'])
            
            if message:
                # Broadcast to ALL participants
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': message.id,
                        'sender_id': self.user.id,
                        'sender_name': self.user.display_name,
                        'content': content,
                        'timestamp': message.timestamp.isoformat(),
                        'reply_to': reply_to_id,
                        'sentiment_score': message.sentiment_score,
                        'is_flagged': message.is_flagged,
                    }
                )
        
        else:
            # ============================================
            # QUEUE AS PENDING MESSAGE
            # ============================================
            print(f"⏳ Queuing message as pending")
            
            pending_msg = await self.create_pending_message(
                content,
                reply_to_id,
                analysis['sentiment_score'],
                analysis['is_suspicious'],
                availability_info['supervisor']
            )
            
            if pending_msg:
                print(f"✅ Created pending message {pending_msg.id}")
                
                # Send pending confirmation to sender ONLY
                await self.send(text_data=json.dumps({
                    'type': 'message_pending',
                    'pending_message_id': pending_msg.id,
                    'sender_id': self.user.id,
                    'sender_name': self.user.display_name,
                    'content': content,
                    'created_at': pending_msg.created_at.isoformat(),
                    'scheduled_delivery_time': pending_msg.scheduled_delivery_time.isoformat() if pending_msg.scheduled_delivery_time else None,
                    'supervisor_name': availability_info['supervisor'].display_name if availability_info['supervisor'] else 'Supervisor',
                    'delivery_message': f"Message will be delivered when {availability_info['supervisor'].display_name if availability_info['supervisor'] else 'supervisor'} is available",
                    'time_until_delivery': str(pending_msg.time_until_delivery) if pending_msg.time_until_delivery else 'Unknown'
                }))
                
                # Show it in sender's UI as pending
                await self.send(text_data=json.dumps({
                    'type': 'show_pending_message',
                    'pending_message_id': pending_msg.id,
                    'content': content,
                    'created_at': pending_msg.created_at.isoformat(),
                    'status': 'pending',
                    'delivery_info': availability_info['message']
                }))
            else:
                print(f"❌ Failed to create pending message")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to queue your message. Please try again.',
                    'code': 'PENDING_CREATION_FAILED'
                }))

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        if is_typing:
            await self.add_typing_indicator()
        else:
            await self.remove_typing_indicator()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': self.user.id,
                'username': self.user.display_name,
                'is_typing': is_typing
            }
        )
    
    async def handle_reaction(self, data):
        """Handle emoji reaction to message"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        if message_id and emoji:
            reaction = await self.add_reaction(message_id, emoji)
            
            if reaction:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_reaction',
                        'message_id': message_id,
                        'user_id': self.user.id,
                        'username': self.user.display_name,
                        'emoji': emoji
                    }
                )
    
    async def handle_delete(self, data):
        """Handle message deletion"""
        message_id = data.get('message_id')
        
        if message_id:
            deleted = await self.delete_message(message_id)
            
            if deleted:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'message_id': message_id,
                        'deleted_by': self.user.id
                    }
                )
    
    async def handle_mark_room_read(self, data):
        """Handle marking room as read"""
        try:
            incoming_room_id = str(data.get('room_id', ''))
            if str(self.room_id) != incoming_room_id:
                return
        except Exception:
            return
        
        await self.update_member_last_read()
    
    # ============================================
    # MESSAGE TYPE HANDLERS (from channel layer)
    # ============================================
    
    async def chat_message(self, event):
        """Send chat message to WebSocket - FIXED for proper display"""
        # Send to ALL users including sender (frontend handles display)
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'reply_to': event.get('reply_to'),
            'sentiment_score': event.get('sentiment_score', 0),
            'is_flagged': event.get('is_flagged', False),
        }))
    
    async def pending_message_delivered(self, event):
        """Handle pending message delivery"""
        await self.send(text_data=json.dumps({
            'type': 'pending_delivered',
            'pending_message_id': event['pending_message_id'],
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'sentiment_score': event.get('sentiment_score', 0),
            'is_flagged': event.get('is_flagged', False),
        }))
    
    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_joined(self, event):
        """Notify when user joins"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
    
    async def user_left(self, event):
        """Notify when user leaves"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
    
    async def message_reaction(self, event):
        """Send reaction notification"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'reaction',
                'message_id': event['message_id'],
                'user_id': event['user_id'],
                'username': event['username'],
                'emoji': event['emoji']
            }))
    
    async def message_deleted(self, event):
        """Send deletion notification"""
        await self.send(text_data=json.dumps({
            'type': 'deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by']
        }))
    
    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    
    @database_sync_to_async
    def check_room_access(self):
        """Check if user has access to the room"""
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def check_supervisor_availability(self):
        """
        FIXED: Check if supervisor is available for immediate messaging
        """
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            print(f"🔍 Checking availability for room {room.id} ({room.room_type})")
            
            # Find supervisor
            supervisor = None
            
            if room.room_type == 'supervisor' and room.group:
                supervisor = room.group.supervisor
                print(f"   Found group supervisor: {supervisor.display_name}")
            
            elif room.room_type == 'direct':
                supervisor = room.participants.filter(role='supervisor').first()
                if supervisor:
                    print(f"   Found DM supervisor: {supervisor.display_name}")
            
            # No supervisor = always available
            if not supervisor:
                print(f"   ✅ No supervisor restrictions")
                return {
                    'is_available': True,
                    'supervisor': None,
                    'message': 'No supervisor restrictions'
                }
            
            # Check if supervisor has schedule enabled
            if not supervisor.schedule_enabled:
                print(f"   ✅ Supervisor schedule not enabled")
                return {
                    'is_available': True,
                    'supervisor': supervisor,
                    'message': 'Supervisor has no schedule restrictions'
                }
            
            # Check availability
            is_available = supervisor.is_available_now()
            
            print(f"   📅 Schedule enabled: Yes")
            print(f"   ⏰ Available now: {is_available}")
            
            if not is_available:
                print(f"   ❌ Supervisor UNAVAILABLE - will queue message")
            
            return {
                'is_available': is_available,
                'supervisor': supervisor,
                'message': supervisor.get_availability_message() if not is_available else 'Supervisor is available'
            }
            
        except Exception as e:
            print(f"❌ Error checking supervisor availability: {e}")
            traceback.print_exc()
            return {
                'is_available': True,
                'supervisor': None,
                'message': 'Error checking availability'
            }
    
    @database_sync_to_async
    def save_message(self, content, reply_to_id, sentiment_score):
        """Save message to database (immediate delivery)"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass
            
            # Import here to avoid circular imports
            from analytics.sentiment import InappropriateContentDetector
            detector = InappropriateContentDetector()
            analysis = detector.analyze_content(content, content_type='chat')
            
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                reply_to=reply_to,
                sentiment_score=sentiment_score,
                is_flagged=analysis['is_suspicious'] or analysis['is_inappropriate']
            )
            
            room.last_message_at = timezone.now()
            room.save(update_fields=['last_message_at'])
            
            print(f"✅ Saved message {message.id}")
            return message
        except Exception as e:
            print(f"❌ Error saving message: {e}")
            traceback.print_exc()
            return None
    
    @database_sync_to_async
    def create_pending_message(self, content, reply_to_id, sentiment_score, is_flagged, supervisor):
        """Create a pending message that will be delivered later"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass
            
            # Create pending message
            pending_msg = PendingMessage.objects.create(
                room=room,
                sender=self.user,
                content=content,
                reply_to=reply_to,
                target_supervisor=supervisor,
                sentiment_score=sentiment_score,
                is_flagged=is_flagged,
                status='pending'
            )
            
            # Calculate delivery time
            delivery_time = pending_msg.calculate_delivery_time()
            pending_msg.scheduled_delivery_time = delivery_time
            
            # Set expiry (7 days from now)
            pending_msg.expires_at = timezone.now() + timedelta(days=7)
            pending_msg.save()
            
            print(f"✅ Created pending message {pending_msg.id} scheduled for {delivery_time}")
            
            return pending_msg
        except Exception as e:
            print(f"❌ Error creating pending message: {e}")
            traceback.print_exc()
            return None
    
    @database_sync_to_async
    def analyze_content(self, content):
        """Analyze message content for sentiment and inappropriate content"""
        try:
            # Import here to avoid circular imports
            from analytics.sentiment import InappropriateContentDetector
            from textblob import TextBlob
            
            detector = InappropriateContentDetector()
            analysis = detector.analyze_content(content, content_type='chat')
            
            blob = TextBlob(content)
            sentiment_score = blob.sentiment.polarity
            
            return {
                'sentiment_score': sentiment_score,
                'is_inappropriate': analysis['is_inappropriate'],
                'is_suspicious': analysis['is_suspicious'],
                'inappropriate_issues': analysis.get('inappropriate_issues', [])
            }
        except Exception as e:
            print(f"❌ Content analysis error: {e}")
            traceback.print_exc()
            return {
                'sentiment_score': 0,
                'is_inappropriate': False,
                'is_suspicious': False,
                'inappropriate_issues': []
            }
    
    @database_sync_to_async
    def update_user_status(self, online):
        """Update user's online status in room"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            member, created = ChatRoomMember.objects.get_or_create(
                room=room,
                user=self.user
            )
            member.is_online = online
            if online:
                member.update_last_seen()
            else:
                member.save(update_fields=['is_online'])
        except Exception as e:
            print(f"❌ Error updating user status: {e}")
    
    @database_sync_to_async
    def add_typing_indicator(self):
        """Add typing indicator"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            TypingIndicator.objects.update_or_create(
                room=room,
                user=self.user
            )
        except Exception as e:
            print(f"❌ Error adding typing indicator: {e}")
    
    @database_sync_to_async
    def remove_typing_indicator(self):
        """Remove typing indicator"""
        try:
            TypingIndicator.objects.filter(
                room_id=self.room_id,
                user=self.user
            ).delete()
        except Exception as e:
            print(f"❌ Error removing typing indicator: {e}")
    
    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        """Add emoji reaction to message"""
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            reaction, created = MessageReaction.objects.get_or_create(
                message=message,
                user=self.user,
                emoji=emoji
            )
            return reaction
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message (soft delete)"""
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            
            if message.sender == self.user or self.user.role == 'admin':
                message.soft_delete()
                return True
            
            return False
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_member_last_read(self):
        """Update last_read_at for this user & room"""
        try:
            member, created = ChatRoomMember.objects.get_or_create(
                room_id=self.room_id,
                user=self.user
            )
            member.last_read_at = timezone.now()
            member.save(update_fields=['last_read_at'])
        except Exception as e:
            print(f"❌ Error updating last_read_at: {e}")