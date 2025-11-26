# File: analytics/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import SupervisorFeedback


class SupervisorFeedbackForm(forms.ModelForm):
    """Form for supervisors to add feedback log sheet entries"""

    class Meta:
        model = SupervisorFeedback
        fields = [
            'date', 'context', 'remarks', 'rating',
            'action_required', 'follow_up_required', 'follow_up_date',
            'is_visible_to_student'
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'context': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief context (e.g., Weekly review, Mid-semester feedback)'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Detailed feedback and remarks about student progress, areas of improvement, strengths, etc.'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-control'
            }),
            'action_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'is_visible_to_student': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'date': 'Feedback Date',
            'context': 'Context/Session Type',
            'remarks': 'Feedback Remarks',
            'rating': 'Performance Rating',
            'action_required': 'Requires Immediate Action',
            'follow_up_required': 'Follow-up Required',
            'follow_up_date': 'Follow-up Date',
            'is_visible_to_student': 'Visible to Student',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set follow_up_date as required only if follow_up_required is checked
        self.fields['follow_up_date'].required = False

        # Add help text
        self.fields['action_required'].help_text = 'Check if this feedback requires immediate action from the student'
        self.fields['follow_up_required'].help_text = 'Check if a follow-up meeting is needed'
        self.fields['is_visible_to_student'].help_text = 'Uncheck to hide this feedback from the student'

    def clean(self):
        cleaned_data = super().clean()
        follow_up_required = cleaned_data.get('follow_up_required')
        follow_up_date = cleaned_data.get('follow_up_date')

        # Validate that follow_up_date is provided if follow_up_required is True
        if follow_up_required and not follow_up_date:
            raise ValidationError('Please specify a follow-up date when follow-up is required.')

        return cleaned_data


class SupervisorReviewForm(forms.Form):
    """Form for supervisor to review event submissions"""

    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Review Decision'
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide detailed remarks about this submission...'
        }),
        label='Remarks',
        required=True
    )
    rating = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Rating (1-5)',
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        remarks = cleaned_data.get('remarks')

        if action == 'approve' and not cleaned_data.get('rating'):
            raise ValidationError('Please provide a rating when approving a submission.')

        if not remarks or len(remarks.strip()) < 10:
            raise ValidationError('Please provide detailed remarks (at least 10 characters).')

        return cleaned_data


class AdminReviewForm(forms.Form):
    """Form for admin to give final approval/rejection"""

    ACTION_CHOICES = [
        ('approve', 'Final Approval'),
        ('reject', 'Final Rejection'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Final Decision'
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide final remarks about this submission...'
        }),
        label='Admin Remarks',
        required=True
    )
    rating = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Final Rating (1-5)',
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if action == 'approve' and not cleaned_data.get('rating'):
            raise ValidationError('Please provide a rating when giving final approval.')

        return cleaned_data