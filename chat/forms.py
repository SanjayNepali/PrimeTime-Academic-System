# File: chat/forms.py - COMPLETE FIXED VERSION

from django import forms
from django.core.exceptions import ValidationError
from .models import ChatRoom
from accounts.models import User
from groups.models import Group, GroupMembership


class CreateChatRoomForm(forms.ModelForm):
    """Form for creating chat rooms with supervisor schedule support"""
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'room_type', 'group', 'participants', 'is_frozen']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room name'
            }),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'participants': forms.CheckboxSelectMultiple(),
            'is_frozen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configure group field
        if self.user:
            if self.user.role == 'supervisor':
                # Supervisors can only see their own groups
                self.fields['group'].queryset = Group.objects.filter(
                    supervisor=self.user,
                    is_active=True
                )
            elif self.user.role == 'admin':
                # Admins can see all groups
                self.fields['group'].queryset = Group.objects.filter(is_active=True)
        
        # Configure participants field
        self.fields['participants'].queryset = User.objects.filter(
            role__in=['student', 'supervisor'],
            is_active=True
        )
        
        # Add help text
        self.fields['is_frozen'].help_text = (
            'Enable time restrictions based on your schedule settings'
        )
    
    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        group = cleaned_data.get('group')
        name = cleaned_data.get('name')
        
        # Supervisor chat validation
        if room_type == 'supervisor':
            if not group:
                raise ValidationError('Supervisor chat rooms must be linked to a group.')
            
            # Check for existing supervisor chat for this group
            existing_supervisor_chat = ChatRoom.objects.filter(
                room_type='supervisor',
                group=group,
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_supervisor_chat.exists():
                raise ValidationError(
                    f'This group already has a supervisor chat room: '
                    f'{existing_supervisor_chat.first().name}'
                )
        
        # Check for duplicate names
        if name:
            existing_rooms = ChatRoom.objects.filter(
                name__iexact=name.strip(),
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_rooms.exists():
                raise ValidationError(f'A chat room with name "{name}" already exists.')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # If supervisor chat and frozen, copy supervisor's schedule
        if instance.room_type == 'supervisor' and instance.is_frozen and instance.group:
            supervisor = instance.group.supervisor
            if supervisor.schedule_enabled:
                instance.schedule_start_time = supervisor.schedule_start_time
                instance.schedule_end_time = supervisor.schedule_end_time
                instance.schedule_days = supervisor.schedule_days
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


class UpdateChatRoomForm(forms.ModelForm):
    """Form for updating chat rooms - FIXED with checkbox participants"""
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'participants', 'is_frozen']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Room name'
            }),
            'participants': forms.CheckboxSelectMultiple(),
            'is_frozen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # CRITICAL FIX: Only show students not already in ANY supervisor chat
        if self.instance and self.instance.room_type == 'supervisor' and self.instance.group:
            # Get all students from this supervisor's group
            group_students = User.objects.filter(
                group_memberships__group=self.instance.group,
                group_memberships__is_active=True,
                role='student'
            )
            
            # Get students already in OTHER supervisor chats
            students_in_supervisor_chats = User.objects.filter(
                chat_rooms__room_type='supervisor',
                chat_rooms__is_active=True
            ).exclude(
                chat_rooms=self.instance  # Exclude current room
            ).distinct()
            
            # Available students = group students NOT in other supervisor chats
            available_students = group_students.exclude(
                id__in=students_in_supervisor_chats.values_list('id', flat=True)
            )
            
            self.fields['participants'].queryset = available_students
        else:
            # For non-supervisor chats, show all active users
            self.fields['participants'].queryset = User.objects.filter(
                role__in=['student', 'supervisor'],
                is_active=True
            )
        
        # Custom label format with role badges
        self.fields['participants'].label_from_instance = self.label_from_instance
        
        # Help text
        self.fields['is_frozen'].help_text = (
            'Enable time restrictions based on supervisor schedule'
        )
    
    def label_from_instance(self, obj):
        """Custom label format for participants"""
        return f"{obj.display_name} ({obj.get_role_display()})"
    
    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        
        # Check for duplicate names
        if name:
            existing_rooms = ChatRoom.objects.filter(
                name__iexact=name.strip(),
                is_active=True
            ).exclude(pk=self.instance.pk)
            
            if existing_rooms.exists():
                raise ValidationError(f'A chat room with name "{name}" already exists.')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # CRITICAL FIX: Update schedule from supervisor when frozen
        if instance.room_type == 'supervisor' and instance.is_frozen and instance.group:
            supervisor = instance.group.supervisor
            if supervisor.schedule_enabled:
                instance.schedule_start_time = supervisor.schedule_start_time
                instance.schedule_end_time = supervisor.schedule_end_time
                instance.schedule_days = supervisor.schedule_days
            else:
                # If supervisor doesn't have schedule, disable frozen
                instance.is_frozen = False
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance