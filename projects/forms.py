# File: Desktop/Prime/projects/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from .models import Project, ProjectDeliverable, ProjectLogSheet, GroupMeeting, StudentProgressNote, MeetingAttendance


class ProjectForm(forms.ModelForm):
    """Form for students to create/edit projects"""
    
    class Meta:
        model = Project
        fields = ['title', 'description', 'programming_languages']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your project title',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your project in detail...'
            }),
            'programming_languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Django, React, PostgreSQL',
                'help_text': 'Separate technologies with commas'
            })
        }
    
    def clean_title(self):
        """Validate project title"""
        title = self.cleaned_data.get('title')
        if len(title) < 10:
            raise ValidationError('Project title must be at least 10 characters long.')
        return title
    
    def clean_programming_languages(self):
        """Clean and validate programming languages"""
        languages = self.cleaned_data.get('programming_languages')
        # Remove extra spaces and standardize
        cleaned = ', '.join([lang.strip() for lang in languages.split(',') if lang.strip()])
        if not cleaned:
            raise ValidationError('Please specify at least one technology/language.')
        return cleaned


class ProjectSubmitForm(forms.Form):
    """Form to submit project for review"""
    
    confirm = forms.BooleanField(
        required=True,
        label='I confirm that my project details are complete and ready for review',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class ProjectReviewForm(forms.Form):
    """Form for admin to approve/reject projects"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve Project'),
        ('reject', 'Reject Project'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide reason for rejection (required if rejecting)'
        })
    )
    
    def clean(self):
        """Validate that rejection reason is provided when rejecting"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if action == 'reject' and not rejection_reason:
            raise ValidationError('Rejection reason is required when rejecting a project.')
        
        return cleaned_data


class ProjectDeliverableForm(forms.ModelForm):
    """Form for students to submit project deliverables"""
    
    class Meta:
        model = ProjectDeliverable
        fields = ['stage', 'document']
        widgets = {
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.doc,.docx,.pdf,.zip'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        if self.project:
            # Filter out stages that already have deliverables
            existing_stages = ProjectDeliverable.objects.filter(
                project=self.project
            ).values_list('stage', flat=True)
            
            available_choices = [
                choice for choice in ProjectDeliverable.STAGE_CHOICES
                if choice[0] not in existing_stages
            ]
            
            if available_choices:
                self.fields['stage'].choices = available_choices
            else:
                self.fields['stage'].widget.attrs['disabled'] = True
                self.fields['stage'].help_text = 'All deliverables have been submitted.'
    
    def clean_document(self):
        """Validate uploaded file"""
        document = self.cleaned_data.get('document')
        if document:
            # Check file size (max 10MB)
            if document.size > 10 * 1024 * 1024:
                raise ValidationError('File size must not exceed 10MB.')
            
            # Check file extension
            allowed_extensions = ['.doc', '.docx', '.pdf', '.zip']
            file_name = document.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError('Only Word documents, PDFs, and ZIP files are allowed.')
        
        return document


class DeliverableReviewForm(forms.ModelForm):
    """Form for supervisors to review deliverables"""
    
    class Meta:
        model = ProjectDeliverable
        fields = ['marks', 'feedback']
        widgets = {
            'marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'placeholder': 'Enter marks (0-100)'
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide feedback for the student...'
            })
        }
    
    def clean_marks(self):
        """Validate marks"""
        marks = self.cleaned_data.get('marks')
        if marks is not None:
            if marks < 0 or marks > 100:
                raise ValidationError('Marks must be between 0 and 100.')
        return marks


class LogSheetApprovalForm(forms.ModelForm):
    """Form for supervisors to approve/review log sheets"""
    
    class Meta:
        model = ProjectLogSheet
        fields = ['supervisor_remarks', 'supervisor_rating']
        widgets = {
            'supervisor_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide feedback on this week\'s progress...'
            }),
            'supervisor_rating': forms.Select(
                attrs={'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the choices for supervisor_rating dynamically
        self.fields['supervisor_rating'].choices = [(i, f"{i} - {'⭐' * i}") for i in range(1, 6)]
    
    def clean_supervisor_remarks(self):
        remarks = self.cleaned_data.get('supervisor_remarks')
        if not remarks or len(remarks) < 10:
            raise ValidationError('Please provide detailed feedback (at least 10 characters).')
        return remarks


class MeetingScheduleForm(forms.ModelForm):
    """Form for scheduling meetings with students"""
    
    class Meta:
        model = GroupMeeting
        fields = ['meeting_type', 'scheduled_date', 'duration_minutes', 
                  'location', 'meeting_link', 'agenda']
        widgets = {
            'meeting_type': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 15,
                'max': 180,
                'step': 15
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Office 304 or Online'
            }),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zoom/Google Meet link (optional)'
            }),
            'agenda': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What will be discussed in this meeting?'
            }),
        }


class MeetingMinutesForm(forms.ModelForm):
    """Form for recording meeting minutes"""
    
    class Meta:
        model = GroupMeeting
        fields = ['discussion_summary', 'action_items', 'next_steps', 'supervisor_notes']
        widgets = {
            'discussion_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Summarize what was discussed...'
            }),
            'action_items': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List action items for the student...'
            }),
            'next_steps': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What are the next steps?'
            }),
            'supervisor_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Private notes (not visible to student)'
            }),
        }


class ProgressNoteForm(forms.ModelForm):
    """Form for adding supervisor notes"""
    
    class Meta:
        model = StudentProgressNote
        fields = ['category', 'note', 'is_visible_to_student']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add your observations, concerns, or notes...'
            }),
            'is_visible_to_student': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# ===== NEWLY ADDED FORMS =====

class GroupMeetingScheduleForm(forms.ModelForm):
    """Form for scheduling group meetings"""
    
    class Meta:
        model = GroupMeeting
        fields = ['meeting_type', 'scheduled_date', 'duration_minutes', 
                  'location', 'meeting_link', 'agenda']
        widgets = {
            'meeting_type': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 15,
                'max': 180,
                'step': 15,
                'value': 60
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Room 304 or Online'
            }),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zoom/Google Meet link (optional)'
            }),
            'agenda': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What will be discussed in this group meeting?'
            }),
        }


class GroupMeetingMinutesForm(forms.Form):
    """Form for recording meeting minutes for group meetings"""
    
    discussion_summary = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Summarize what was discussed...'
        }),
        label='Discussion Summary',
        required=True
    )
    
    action_items = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List action items for students...'
        }),
        label='Action Items',
        required=True
    )
    
    next_steps = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'What are the next steps? When is the next meeting?'
        }),
        label='Next Steps',
        required=True
    )
    
    supervisor_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Private notes (not visible to students)'
        }),
        label='Supervisor Private Notes',
        required=False
    )
    
    def clean_discussion_summary(self):
        """Validate discussion summary"""
        summary = self.cleaned_data.get('discussion_summary')
        if len(summary.strip()) < 20:
            raise ValidationError('Discussion summary must be at least 20 characters long.')
        return summary
    
    def clean_action_items(self):
        """Validate action items"""
        action_items = self.cleaned_data.get('action_items')
        if len(action_items.strip()) < 10:
            raise ValidationError('Action items must be at least 10 characters long.')
        return action_items


class MeetingAttendanceForm(forms.ModelForm):
    """Form for recording student attendance in meetings"""
    
    class Meta:
        model = MeetingAttendance
        fields = ['attended', 'notes']
        widgets = {
            'attended': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes about this student\'s attendance...'
            }),
        }


# MeetingAttendanceFormSet factory
MeetingAttendanceFormSet = inlineformset_factory(
    GroupMeeting,
    MeetingAttendance,
    form=MeetingAttendanceForm,
    extra=0,
    can_delete=False,
    fields=['attended', 'notes']
)


class StudentLogSheetForm(forms.ModelForm):
    """Form for students to fill in their log sheets"""
    
    class Meta:
        model = ProjectLogSheet
        fields = ['tasks_completed', 'challenges_faced', 'next_week_plan', 
                  'hours_spent', 'attachment']
        widgets = {
            'tasks_completed': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What did you accomplish this week?'
            }),
            'challenges_faced': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What challenges or blockers did you face?'
            }),
            'next_week_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What do you plan to work on next week?'
            }),
            'hours_spent': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.5
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean_hours_spent(self):
        """Validate hours spent"""
        hours = self.cleaned_data.get('hours_spent')
        if hours is not None and hours < 0:
            raise ValidationError('Hours spent cannot be negative.')
        return hours
    
    def clean_tasks_completed(self):
        """Validate tasks completed field"""
        tasks = self.cleaned_data.get('tasks_completed')
        if not tasks or len(tasks.strip()) < 10:
            raise ValidationError('Please provide a detailed description of tasks completed (at least 10 characters).')
        return tasks
    
    def clean_attachment(self):
        """Validate uploaded attachment"""
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Check file size (max 5MB)
            if attachment.size > 5 * 1024 * 1024:
                raise ValidationError('Attachment size must not exceed 5MB.')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.zip']
            file_name = attachment.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError('Only PDF, Word documents, images, and ZIP files are allowed.')
        
        return attachment