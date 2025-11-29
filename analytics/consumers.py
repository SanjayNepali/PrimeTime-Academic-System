# ============================================
# FILE 2: analytics/consumers.py (CREATE THIS NEW FILE)
# ============================================

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class StressUpdateConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time stress level updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Determine which group to join based on user role
        if self.user.role == 'student':
            # Students join their own stress room
            self.room_group_name = f'stress_student_{self.user.id}'
        elif self.user.role == 'supervisor':
            # Supervisors join a group for all their students
            self.room_group_name = f'stress_supervisor_{self.user.id}'
        elif self.user.role == 'admin':
            # Admins join the global stress room
            self.room_group_name = 'stress_admin_all'
        else:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"✅ Stress WebSocket connected for {self.user.display_name} (role: {self.user.role})")
        
        # Send initial stress data
        await self.send_initial_stress_data()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"🔴 Stress WebSocket disconnected for {self.user.display_name}")
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'request_stress_update':
                student_id = data.get('student_id')
                if student_id:
                    await self.send_stress_update(student_id)
                else:
                    await self.send_initial_stress_data()
        except Exception as e:
            logger.error(f"❌ Error in receive: {e}")
    
    async def stress_level_updated(self, event):
        """Handler for stress level updates from channel layer"""
        await self.send(text_data=json.dumps({
            'type': 'stress_update',
            'student_id': event['student_id'],
            'student_name': event['student_name'],
            'stress_level': event['stress_level'],
            'stress_category': event['stress_category'],
            'chat_sentiment': event.get('chat_sentiment', 0),
            'deadline_pressure': event.get('deadline_pressure', 0),
            'workload': event.get('workload', 0),
            'social_isolation': event.get('social_isolation', 0),
            'timestamp': event['timestamp']
        }))
    
    async def send_initial_stress_data(self):
        """Send initial stress data when user connects"""
        stress_data = await self.get_initial_stress_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'data': stress_data
        }))
    
    async def send_stress_update(self, student_id):
        """Send stress update for specific student"""
        stress_data = await self.get_student_stress(student_id)
        if stress_data:
            await self.send(text_data=json.dumps({
                'type': 'stress_update',
                **stress_data
            }))
    
    @database_sync_to_async
    def get_initial_stress_data(self):
        """Get initial stress data based on user role"""
        from analytics.models import StressLevel
        from groups.models import GroupMembership
        from accounts.models import User
        
        if self.user.role == 'student':
            # Get student's own stress
            stress = StressLevel.objects.filter(
                student=self.user
            ).order_by('-calculated_at').first()
            
            if stress:
                return [{
                    'student_id': self.user.id,
                    'student_name': self.user.display_name,
                    'stress_level': float(stress.level),
                    'stress_category': stress.stress_category,
                    'chat_sentiment': float(stress.chat_sentiment_score),
                    'deadline_pressure': float(stress.deadline_pressure),
                    'workload': float(stress.workload_score),
                    'social_isolation': float(stress.social_isolation_score),
                    'timestamp': stress.calculated_at.isoformat()
                }]
        
        elif self.user.role == 'supervisor':
            # Get all students supervised by this supervisor
            supervised_students = User.objects.filter(
                group_memberships__group__supervisor=self.user,
                group_memberships__is_active=True
            ).distinct()
            
            stress_data = []
            for student in supervised_students:
                stress = StressLevel.objects.filter(
                    student=student
                ).order_by('-calculated_at').first()
                
                if stress:
                    stress_data.append({
                        'student_id': student.id,
                        'student_name': student.display_name,
                        'stress_level': float(stress.level),
                        'stress_category': stress.stress_category,
                        'chat_sentiment': float(stress.chat_sentiment_score),
                        'deadline_pressure': float(stress.deadline_pressure),
                        'workload': float(stress.workload_score),
                        'social_isolation': float(stress.social_isolation_score),
                        'timestamp': stress.calculated_at.isoformat()
                    })
            
            return stress_data
        
        elif self.user.role == 'admin':
            # Get all students with recent stress data (limit to last 50)
            recent_stress = StressLevel.objects.filter(
                calculated_at__gte=timezone.now() - timedelta(days=1)
            ).select_related('student').order_by('-calculated_at')[:50]
            
            # Group by student to get latest for each
            stress_dict = {}
            for stress in recent_stress:
                if stress.student.id not in stress_dict:
                    stress_dict[stress.student.id] = {
                        'student_id': stress.student.id,
                        'student_name': stress.student.display_name,
                        'stress_level': float(stress.level),
                        'stress_category': stress.stress_category,
                        'chat_sentiment': float(stress.chat_sentiment_score),
                        'deadline_pressure': float(stress.deadline_pressure),
                        'workload': float(stress.workload_score),
                        'social_isolation': float(stress.social_isolation_score),
                        'timestamp': stress.calculated_at.isoformat()
                    }
            
            return list(stress_dict.values())
        
        return []
    
    @database_sync_to_async
    def get_student_stress(self, student_id):
        """Get stress data for specific student"""
        from analytics.models import StressLevel
        from accounts.models import User
        
        try:
            student = User.objects.get(id=student_id)
            stress = StressLevel.objects.filter(
                student=student
            ).order_by('-calculated_at').first()
            
            if stress:
                return {
                    'student_id': student.id,
                    'student_name': student.display_name,
                    'stress_level': float(stress.level),
                    'stress_category': stress.stress_category,
                    'chat_sentiment': float(stress.chat_sentiment_score),
                    'deadline_pressure': float(stress.deadline_pressure),
                    'workload': float(stress.workload_score),
                    'social_isolation': float(stress.social_isolation_score),
                    'timestamp': stress.calculated_at.isoformat()
                }
        except Exception as e:
            logger.error(f"❌ Error getting student stress: {e}")
        
        return None
