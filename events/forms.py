# File: events/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event, EventAttendance, Calendar, Notification, EventSubmission
from accounts.models import User
from groups.models import Group


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'start_datetime', 'end_datetime',
            'all_day', 'location', 'virtual_link', 'batch_year', 'group', 'organizer',
            'participants', 'priority', 'is_mandatory', 'send_reminders', 'reminder_hours_before'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'event_type': forms.Select(attrs={'class': 'form-control'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'all_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'virtual_link': forms.URLInput(attrs={'class': 'form-control'}),
            'batch_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'organizer': forms.Select(attrs={'class': 'form-control'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 8}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_hours_before': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        
        if start_datetime and end_datetime:
            now = timezone.now()
            
            # Prevent past dates
            if start_datetime < now:
                raise ValidationError("Cannot schedule events in the past.")
            
            # Ensure end time is after start time
            if end_datetime <= start_datetime:
                raise ValidationError("End time must be after start time.")
        
        return cleaned_data

class CalendarForm(forms.ModelForm):
    class Meta:
        model = Calendar
        fields = '__all__'
        exclude = ['created_by']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proposal_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mid_defense_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mid_defense_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pre_defense_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pre_defense_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'final_defense_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'final_defense_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EventSubmissionForm(forms.ModelForm):
    """Form for students to submit files to deadline events"""

    class Meta:
        model = EventSubmission
        fields = ['submission_file', 'submission_notes']
        widgets = {
            'submission_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx,.zip'
            }),
            'submission_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional notes about your submission...'
            }),
        }
        labels = {
            'submission_file': 'Upload File',
            'submission_notes': 'Submission Notes (Optional)',
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event

        # Customize file input based on event requirements
        if event:
            if event.submission_file_type:
                file_types = event.submission_file_type.lower()
                self.fields['submission_file'].help_text = f'Required file type: {event.submission_file_type}'

                # Update accept attribute based on required file type
                accept_map = {
                    'pdf': '.pdf',
                    'docx': '.doc,.docx',
                    'word': '.doc,.docx',
                    'ppt': '.ppt,.pptx',
                    'pptx': '.ppt,.pptx',
                    'presentation': '.ppt,.pptx',
                }
                for key, accept_val in accept_map.items():
                    if key in file_types:
                        self.fields['submission_file'].widget.attrs['accept'] = accept_val
                        break

            if event.max_file_size_mb:
                self.fields['submission_file'].help_text += f' | Max size: {event.max_file_size_mb}MB'

            if event.submission_instructions:
                self.fields['submission_notes'].help_text = f'Instructions: {event.submission_instructions}'

    def clean_submission_file(self):
        file = self.cleaned_data.get('submission_file')

        if not file:
            raise ValidationError('Please select a file to upload.')

        # Check file size
        if self.event and self.event.max_file_size_mb:
            max_size_bytes = self.event.max_file_size_mb * 1024 * 1024
            if file.size > max_size_bytes:
                raise ValidationError(
                    f'File size ({file.size / (1024*1024):.2f}MB) exceeds maximum allowed size ({self.event.max_file_size_mb}MB).'
                )

        # Check file type if specified
        if self.event and self.event.submission_file_type:
            allowed_types = self.event.submission_file_type.lower()
            file_ext = file.name.split('.')[-1].lower()

            valid_extensions = []
            if 'pdf' in allowed_types:
                valid_extensions.append('pdf')
            if 'doc' in allowed_types or 'word' in allowed_types:
                valid_extensions.extend(['doc', 'docx'])
            if 'ppt' in allowed_types or 'presentation' in allowed_types:
                valid_extensions.extend(['ppt', 'pptx'])

            if valid_extensions and file_ext not in valid_extensions:
                raise ValidationError(
                    f'Invalid file type. Allowed types: {", ".join(valid_extensions)}'
                )

        return file

class EventDeadlineForm(forms.ModelForm):
    """Extended form for creating deadline events with submission requirements"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'start_datetime', 'end_datetime',
            'location', 'virtual_link', 'batch_year', 'group',
            'participants', 'is_mandatory',
            'requires_submission', 'submission_file_type',
            'submission_instructions', 'late_submission_penalty', 'max_file_size_mb'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'virtual_link': forms.URLInput(attrs={'class': 'form-control'}),
            'batch_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 8}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_submission': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'submission_file_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PDF, DOCX, PPTX'
            }),
            'submission_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Instructions for students on what to submit...'
            }),
            'late_submission_penalty': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            }),
            'max_file_size_mb': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100
            }),
        }
        labels = {
            'requires_submission': 'Requires File Submission',
            'submission_file_type': 'Expected File Type',
            'submission_instructions': 'Submission Instructions',
            'late_submission_penalty': 'Late Submission Penalty (%)',
            'max_file_size_mb': 'Maximum File Size (MB)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set event_type to deadline by default
        self.instance.event_type = 'deadline'

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        requires_submission = cleaned_data.get('requires_submission')
        submission_file_type = cleaned_data.get('submission_file_type')
        
        if start_datetime and end_datetime:
            now = timezone.now()
            
            # Prevent past dates
            if start_datetime < now:
                raise ValidationError("Cannot schedule deadlines in the past.")
            
            # Ensure end time is after start time
            if end_datetime <= start_datetime:
                raise ValidationError("End time must be after start time.")
        
        # If submission is required, file type should be specified
        if requires_submission and not submission_file_type:
            raise ValidationError('Please specify the expected file type when submission is required.')

        return cleaned_data