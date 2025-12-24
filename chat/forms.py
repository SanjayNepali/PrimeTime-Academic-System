# File: chat/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import ChatRoom
from accounts.models import User


class CreateChatRoomForm(forms.ModelForm):
    """Form for creating chat rooms with supervisor schedule integration"""
    
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select Participants',
        help_text='Select users who can access this chat room'
    )
    
    class Meta:
        model = ChatRoom
        fields = [
            'name', 
            'room_type', 
            'participants', 
            'is_frozen'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Group A Discussion'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_frozen': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set up participants queryset based on user role
        if self.user:
            if self.user.role == 'supervisor':
                # For supervisors creating supervisor chat rooms
                # Only show students from their group
                from groups.models import Group
                
                supervised_groups = Group.objects.filter(supervisor=self.user)
                
                # Get students already in supervisor chat rooms
                existing_supervisor_chats = ChatRoom.objects.filter(
                    room_type='supervisor',
                    group__in=supervised_groups
                )
                
                # Get all members from existing supervisor chats
                existing_member_ids = set()
                for chat in existing_supervisor_chats:
                    existing_member_ids.update(
                        chat.participants.filter(role='student').values_list('id', flat=True)
                    )
                
                # Show only students from supervisor's groups who are NOT already in supervisor chats
                available_students = User.objects.filter(
                    student_memberships__group__in=supervised_groups,
                    student_memberships__is_active=True,
                    is_active=True,
                    is_enabled=True,
                    role='student'
                ).exclude(
                    id__in=existing_member_ids
                ).distinct()
                
                self.fields['participants'].queryset = available_students
                
            elif self.user.role == 'admin':
                # Admins can add anyone
                self.fields['participants'].queryset = User.objects.filter(
                    is_active=True,
                    is_enabled=True
                ).exclude(id=self.user.id)
        
        # Update help text for participants
        self.fields['participants'].help_text = (
            'Select students to add to this chat room. '
            'Students already in supervisor chat rooms are excluded.'
        )
        
        # Remove schedule fields from form - they'll be inherited from supervisor
        # We'll handle schedule in the save method
    
    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        is_frozen = cleaned_data.get('is_frozen')
        
        # Validation for supervisor rooms
        if room_type == 'supervisor' and self.user and self.user.role == 'supervisor':
            # Check if supervisor already has a supervisor chat room for their group
            from groups.models import Group
            
            supervised_groups = Group.objects.filter(supervisor=self.user)
            
            if not supervised_groups.exists():
                raise ValidationError('You must be assigned to a group to create a supervisor chat room.')
            
            # Check for existing supervisor chat rooms
            existing_supervisor_chat = ChatRoom.objects.filter(
                room_type='supervisor',
                group__in=supervised_groups
            ).first()
            
            if existing_supervisor_chat and not self.instance.pk:
                raise ValidationError(
                    f'You already have a supervisor chat room: {existing_supervisor_chat.name}. '
                    'Each supervisor can only have one supervisor chat room per group.'
                )
        
        # If frozen is enabled, validate supervisor has schedule settings
        if is_frozen and room_type == 'supervisor':
            if self.user and self.user.role == 'supervisor':
                if not self.user.schedule_enabled:
                    raise ValidationError(
                        'You must enable time restrictions in your account settings before creating a frozen room. '
                        'Go to Profile > Time Restrictions to set your schedule.'
                    )
                
                if not self.user.schedule_start_time or not self.user.schedule_end_time:
                    raise ValidationError(
                        'You must set start and end times in your account settings before creating a frozen room.'
                    )
        
        return cleaned_data
    
    def save(self, commit=True):
        room = super().save(commit=False)
        
        # For supervisor rooms, inherit schedule from supervisor's settings
        if room.room_type == 'supervisor' and self.user and self.user.role == 'supervisor':
            if room.is_frozen and self.user.schedule_enabled:
                room.schedule_start_time = self.user.schedule_start_time
                room.schedule_end_time = self.user.schedule_end_time
                room.schedule_days = self.user.schedule_days
            
            # Link to supervisor's group
            from groups.models import Group
            supervised_group = Group.objects.filter(supervisor=self.user).first()
            if supervised_group:
                room.group = supervised_group
        
        if commit:
            room.save()
            
            # Add participants
            participants = self.cleaned_data.get('participants')
            if participants:
                room.participants.add(*participants)
            
            # Always add the creator
            if self.user:
                room.participants.add(self.user)
            
            # Save many-to-many
            self.save_m2m()
        
        return room


class UpdateChatRoomForm(forms.ModelForm):
    """Form for updating chat room settings"""
    
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select Participants'
    )
    
    class Meta:
        model = ChatRoom
        fields = [
            'name',
            'is_frozen',
            'participants'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Room name'
            }),
            'is_frozen': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set up participants queryset
        if self.user and self.instance:
            if self.user.role == 'supervisor' and self.instance.room_type == 'supervisor':
                # For supervisor rooms, show students from their group
                from groups.models import Group
                
                supervised_groups = Group.objects.filter(supervisor=self.user)
                
                # Get students already in OTHER supervisor chat rooms
                existing_supervisor_chats = ChatRoom.objects.filter(
                    room_type='supervisor',
                    group__in=supervised_groups
                ).exclude(id=self.instance.id)
                
                existing_member_ids = set()
                for chat in existing_supervisor_chats:
                    existing_member_ids.update(
                        chat.participants.filter(role='student').values_list('id', flat=True)
                    )
                
                # Show students from group not in other supervisor chats
                available_students = User.objects.filter(
                    student_memberships__group__in=supervised_groups,
                    student_memberships__is_active=True,
                    is_active=True,
                    is_enabled=True,
                    role='student'
                ).exclude(
                    id__in=existing_member_ids
                ).distinct()
                
                self.fields['participants'].queryset = available_students
                
                # Set initial participants
                self.fields['participants'].initial = self.instance.participants.filter(
                    role='student'
                )
            
            elif self.user.role == 'admin':
                self.fields['participants'].queryset = User.objects.filter(
                    is_active=True,
                    is_enabled=True
                ).exclude(id=self.user.id)
                
                self.fields['participants'].initial = self.instance.participants.all()
    
    def clean(self):
        cleaned_data = super().clean()
        is_frozen = cleaned_data.get('is_frozen')
        
        # If frozen is enabled for supervisor room, check supervisor settings
        if is_frozen and self.instance.room_type == 'supervisor':
            if self.user and self.user.role == 'supervisor':
                if not self.user.schedule_enabled:
                    raise ValidationError(
                        'You must enable time restrictions in your account settings. '
                        'Go to Profile > Time Restrictions to set your schedule.'
                    )
                
                if not self.user.schedule_start_time or not self.user.schedule_end_time:
                    raise ValidationError(
                        'You must set start and end times in your account settings.'
                    )
        
        return cleaned_data
    
    def save(self, commit=True):
        room = super().save(commit=False)
        
        # Update schedule from supervisor's current settings
        if room.room_type == 'supervisor' and self.user and self.user.role == 'supervisor':
            if room.is_frozen and self.user.schedule_enabled:
                room.schedule_start_time = self.user.schedule_start_time
                room.schedule_end_time = self.user.schedule_end_time
                room.schedule_days = self.user.schedule_days
            else:
                # Clear schedule if not frozen
                room.schedule_start_time = None
                room.schedule_end_time = None
                room.schedule_days = ''
        
        if commit:
            room.save()
            
            # Update participants
            participants = self.cleaned_data.get('participants')
            if participants is not None:
                # Remove old student participants
                room.participants.remove(
                    *room.participants.filter(role='student')
                )
                
                # Add new participants
                room.participants.add(*participants)
                
                # Ensure supervisor is always included
                if self.user:
                    room.participants.add(self.user)
            
            self.save_m2m()
        
        return room