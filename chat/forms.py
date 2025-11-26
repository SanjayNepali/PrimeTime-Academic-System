# ========================================
# File: Desktop/Prime/chat/forms.py
# ========================================

from django import forms
from .models import ChatRoom, Message


class CreateChatRoomForm(forms.ModelForm):
    """Form for creating chat rooms"""
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'room_type', 'participants', 'is_frozen', 'schedule_start_time', 'schedule_end_time', 'schedule_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 8}),
            'is_frozen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'schedule_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mon,Tue,Wed,Thu,Fri'})
        }