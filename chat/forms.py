# File: chat/forms.py - COMPLETELY FIXED

from django import forms
from django.core.exceptions import ValidationError
from .models import ChatRoom
from accounts.models import User


class CreateChatRoomForm(forms.ModelForm):
    """Form for creating chat rooms with FIXED validation"""
    
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
        
        if self.user:
            if self.user.role == 'supervisor':
                # Supervisors creating supervisor chat rooms
                from groups.models import Group
                
                supervised_groups = Group.objects.filter(supervisor=self.user)
                
                if not supervised_groups.exists():
                    self.fields['participants'].queryset = User.objects.none()
                    self.fields['participants'].help_text = 'You must be assigned to a group first.'
                    return
                
                # Get students from supervisor's groups
                group_students = User.objects.filter(
                    student_memberships__group__in=supervised_groups,
                    student_memberships__is_active=True,
                    is_active=True,
                    is_enabled=True,
                    role='student'
                ).distinct()
                
                # FIXED: Filter out students already in ANY supervisor chat
                available_students = []
                for student in group_students:
                    in_supervisor_chat = ChatRoom.objects.filter(
                        room_type='supervisor',
                        participants=student,
                        is_active=True
                    ).exists()
                    
                    if not in_supervisor_chat:
                        available_students.append(student.id)
                
                self.fields['participants'].queryset = User.objects.filter(id__in=available_students)
                
                if not available_students:
                    self.fields['participants'].help_text = (
                        '⚠️ All students from your group are already in supervisor chat rooms. '
                        'Each student can only be in one supervisor chat.'
                    )
                else:
                    self.fields['participants'].label_from_instance = lambda obj: f"{obj.display_name} (Student)"
                
            elif self.user.role == 'admin':
                # CRITICAL FIX: Admins can add ANYONE including themselves
                # Remove the exclude(pk=self.user.pk) that was blocking admin
                self.fields['participants'].queryset = User.objects.filter(
                    is_active=True,
                    is_enabled=True
                ).order_by('role', 'first_name', 'last_name')
                
                self.fields['participants'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.get_role_display()})"
        
        self.fields['participants'].help_text = (
            'Select users to add to this chat room. '
            'Students already in supervisor chat rooms are excluded.'
        )
    
    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        is_frozen = cleaned_data.get('is_frozen')
        name = cleaned_data.get('name')
        participants = cleaned_data.get('participants', [])
        
        print(f"🔍 Form validation: room_type={room_type}, name={name}")
        
        # FIXED: Validate supervisor rooms more strictly
        if room_type == 'supervisor':
            if self.user and self.user.role == 'supervisor':
                from groups.models import Group
                
                supervised_groups = Group.objects.filter(supervisor=self.user)
                
                if not supervised_groups.exists():
                    raise ValidationError('❌ You must be assigned to a group to create a supervisor chat room.')
                
                # CRITICAL FIX: Check if supervisor already has supervisor chat
                existing_supervisor_chat = ChatRoom.objects.filter(
                    room_type='supervisor',
                    group__in=supervised_groups,
                    is_active=True
                ).first()
                
                if existing_supervisor_chat and not self.instance.pk:
                    raise ValidationError(
                        f'❌ You already have a supervisor chat room: "{existing_supervisor_chat.name}". '
                        'Each supervisor can only have ONE supervisor chat room per group.'
                    )
            
            elif self.user and self.user.role == 'admin':
                # CRITICAL FIX: Admin creating supervisor room - validate students
                for participant in participants:
                    if participant.role == 'student':
                        # Check if student is already in ANY supervisor chat
                        existing_supervisor_chats = ChatRoom.objects.filter(
                            room_type='supervisor',
                            participants=participant,
                            is_active=True
                        ).exclude(id=self.instance.pk if self.instance else None)
                        
                        if existing_supervisor_chats.exists():
                            existing_chat = existing_supervisor_chats.first()
                            raise ValidationError(
                                f'❌ Student "{participant.display_name}" is already in supervisor chat room: '
                                f'"{existing_chat.name}". Each student can only be in ONE supervisor chat.'
                            )
        
        # FIXED: Check for duplicate chat room names (case insensitive)
        if name:
            name_clean = name.strip()
            existing_rooms = ChatRoom.objects.filter(
                name__iexact=name_clean,
                is_active=True
            ).exclude(id=self.instance.pk if self.instance else None)
            
            if existing_rooms.exists():
                raise ValidationError(f'❌ A chat room with name "{name_clean}" already exists. Please choose a different name.')
        
        # Validate frozen room settings
        if is_frozen and room_type == 'supervisor':
            if self.user and self.user.role == 'supervisor':
                if not self.user.schedule_enabled:
                    raise ValidationError(
                        '❌ You must enable time restrictions in your account settings before creating a frozen room. '
                        'Go to Profile → Time Restrictions to set your schedule.'
                    )
                
                if not self.user.schedule_start_time or not self.user.schedule_end_time:
                    raise ValidationError(
                        '❌ You must set start and end times in your account settings before creating a frozen room.'
                    )
        
        return cleaned_data
    
    def save(self, commit=True):
        room = super().save(commit=False)
        
        # For supervisor rooms, inherit schedule from supervisor
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
            
            # FIXED: Add participants properly
            participants = self.cleaned_data.get('participants', [])
            if participants:
                # Add selected participants (excluding creator to avoid duplication)
                participants_to_add = [p for p in participants if p != self.user]
                if participants_to_add:
                    room.participants.add(*participants_to_add)
            
            # Always add creator if not already included
            if self.user and self.user not in room.participants.all():
                room.participants.add(self.user)
            
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
        
        if self.user and self.instance:
            if self.user.role == 'supervisor' and self.instance.room_type == 'supervisor':
                from groups.models import Group
                
                supervised_groups = Group.objects.filter(supervisor=self.user)
                
                # Get students in OTHER supervisor chats
                existing_supervisor_chats = ChatRoom.objects.filter(
                    room_type='supervisor',
                    group__in=supervised_groups
                ).exclude(id=self.instance.id)
                
                existing_member_ids = set()
                for chat in existing_supervisor_chats:
                    existing_member_ids.update(
                        chat.participants.filter(role='student').values_list('id', flat=True)
                    )
                
                # Show available students
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
                self.fields['participants'].initial = self.instance.participants.filter(role='student')
                self.fields['participants'].label_from_instance = lambda obj: f"{obj.display_name} (Student)"
            
            elif self.user.role == 'admin':
                # CRITICAL FIX: Admin can select anyone including themselves
                self.fields['participants'].queryset = User.objects.filter(
                    is_active=True,
                    is_enabled=True
                ).order_by('role', 'first_name', 'last_name')
                
                # Set initial to ALL participants
                self.fields['participants'].initial = self.instance.participants.all()
                self.fields['participants'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.get_role_display()})"
    
    def clean(self):
        cleaned_data = super().clean()
        is_frozen = cleaned_data.get('is_frozen')
        name = cleaned_data.get('name')
        
        # Check for duplicate names
        if name:
            name_clean = name.strip()
            existing_rooms = ChatRoom.objects.filter(
                name__iexact=name_clean,
                is_active=True
            ).exclude(id=self.instance.pk if self.instance else None)
            
            if existing_rooms.exists():
                raise ValidationError(f'❌ A chat room with name "{name_clean}" already exists.')
        
        # Validate frozen settings
        if is_frozen and self.instance.room_type == 'supervisor':
            if self.user and self.user.role == 'supervisor':
                if not self.user.schedule_enabled:
                    raise ValidationError(
                        '❌ You must enable time restrictions in your account settings. '
                        'Go to Profile → Time Restrictions to set your schedule.'
                    )
                
                if not self.user.schedule_start_time or not self.user.schedule_end_time:
                    raise ValidationError(
                        '❌ You must set start and end times in your account settings.'
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
                room.schedule_start_time = None
                room.schedule_end_time = None
                room.schedule_days = ''
        
        if commit:
            room.save()
            
            # Update participants
            participants = self.cleaned_data.get('participants')
            if participants is not None:
                # Remove all non-creator participants first
                if room.room_type == 'supervisor' and self.user and self.user.role == 'supervisor':
                    room.participants.remove(*room.participants.filter(role='student'))
                else:
                    room.participants.remove(*room.participants.exclude(id=self.user.id))
                
                # Add new participants (excluding creator)
                participants_to_add = [p for p in participants if p != self.user]
                if participants_to_add:
                    room.participants.add(*participants_to_add)
                
                # Ensure creator is included
                if self.user and self.user not in room.participants.all():
                    room.participants.add(self.user)
            
            self.save_m2m()
        
        return room