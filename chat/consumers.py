# File: Desktop/Prime/chat/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import ChatRoom, Message, ChatRoomMember, TypingIndicator, MessageReaction
from accounts.models import User
from analytics.sentiment import AdvancedSentimentAnalyzer, InappropriateContentDetector


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if room exists and user has access
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Mark user as online
        await self.update_user_status(online=True)
        
        # Accept connection
        await self.accept()
        
        # Notify others that user joined
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
        # Mark user as offline
        await self.update_user_status(online=False)
        
        # Remove typing indicator
        await self.remove_typing_indicator()
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.display_name,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Leave room group
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
            elif message_type == 'read':
                await self.handle_read(data)
            elif message_type == 'reaction':
                await self.handle_reaction(data)
            elif message_type == 'delete':
                await self.handle_delete(data)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_message(self, data):
        """Handle new chat message"""
        content = data.get('message', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return
        
        # Check for inappropriate content
        analysis = await self.analyze_content(content)
        
        if analysis['is_inappropriate']:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Your message contains inappropriate content and cannot be sent.',
                'details': analysis['inappropriate_issues']
            }))
            return
        
        # Save message to database
        message = await self.save_message(content, reply_to_id, analysis['sentiment_score'])
        
        if message:
            # Send message to room group
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
                    'is_flagged': message.is_flagged
                }
            )
            
            # If flagged as suspicious, notify admins
            if analysis['is_suspicious']:
                await self.notify_admins_suspicious_content(message, analysis)
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        if is_typing:
            await self.add_typing_indicator()
        else:
            await self.remove_typing_indicator()
        
        # Broadcast typing status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': self.user.id,
                'username': self.user.display_name,
                'is_typing': is_typing
            }
        )
    
    async def handle_read(self, data):
        """Handle message read receipt"""
        message_id = data.get('message_id')
        
        if message_id:
            await self.mark_message_read(message_id)
            
            # Update last_read_at for user
            await self.update_last_read()
    
    async def handle_reaction(self, data):
        """Handle emoji reaction to message"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        if message_id and emoji:
            reaction = await self.add_reaction(message_id, emoji)
            
            if reaction:
                # Broadcast reaction
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
                # Broadcast deletion
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'message_id': message_id,
                        'deleted_by': self.user.id
                    }
                )
    
    # Message type handlers (for receiving from channel layer)
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'reply_to': event.get('reply_to'),
            'sentiment_score': event.get('sentiment_score', 0),
            'is_flagged': event.get('is_flagged', False)
        }))
    
    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        # Don't send user's own typing status back to them
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
    
    # Database operations
    
    @database_sync_to_async
    def check_room_access(self):
        """Check if user has access to the room"""
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content, reply_to_id, sentiment_score):
        """Save message to database"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            # Check if room is accessible
            if not room.is_accessible_now():
                return None
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass
            
            # Analyze content
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
            
            # Update room's last message time
            room.last_message_at = timezone.now()
            room.save(update_fields=['last_message_at'])
            
            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    @database_sync_to_async
    def analyze_content(self, content):
        """Analyze message content for sentiment and inappropriate content"""
        try:
            detector = InappropriateContentDetector()
            analysis = detector.analyze_content(content, content_type='chat')
            
            # Simple sentiment analysis (can be enhanced)
            from textblob import TextBlob
            blob = TextBlob(content)
            sentiment_score = blob.sentiment.polarity
            
            return {
                'sentiment_score': sentiment_score,
                'is_inappropriate': analysis['is_inappropriate'],
                'is_suspicious': analysis['is_suspicious'],
                'inappropriate_issues': analysis.get('inappropriate_issues', [])
            }
        except Exception as e:
            print(f"Error analyzing content: {e}")
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
            print(f"Error updating user status: {e}")
    
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
            print(f"Error adding typing indicator: {e}")
    
    @database_sync_to_async
    def remove_typing_indicator(self):
        """Remove typing indicator"""
        try:
            TypingIndicator.objects.filter(
                room_id=self.room_id,
                user=self.user
            ).delete()
        except Exception as e:
            print(f"Error removing typing indicator: {e}")
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark message as read"""
        try:
            message = Message.objects.get(id=message_id)
            message.mark_as_read_by(self.user)
        except Message.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_last_read(self):
        """Update user's last read timestamp"""
        try:
            member = ChatRoomMember.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            member.mark_as_read()
        except ChatRoomMember.DoesNotExist:
            pass
    
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
            
            # Only author or admin can delete
            if message.sender == self.user or self.user.role == 'admin':
                message.soft_delete()
                return True
            
            return False
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def notify_admins_suspicious_content(self, message, analysis):
        """Notify admins about suspicious content"""
        try:
            from events.models import Notification
            admins = User.objects.filter(role='admin')
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notification_type='system',
                    title='Suspicious Chat Message Detected',
                    message=f"Message from {self.user.display_name} flagged: {', '.join(analysis.get('suspicious_issues', []))}",
                    link_url=f'/chat/room/{self.room_id}/'
                )
        except Exception as e:
            print(f"Error notifying admins: {e}")