# File: groups/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import Group, GroupMembership
from accounts.models import User


class GroupForm(forms.ModelForm):
    """Form for creating and editing groups"""

    class Meta:
        model = Group
        fields = ['name', 'supervisor', 'batch_year', 'min_students', 'max_students', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Group A'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'batch_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2081'}),
            'min_students': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show supervisors in the supervisor field
        self.fields['supervisor'].queryset = User.objects.filter(role='supervisor', is_active=True)
        self.fields['supervisor'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username})"

    def clean(self):
        cleaned_data = super().clean()
        min_students = cleaned_data.get('min_students')
        max_students = cleaned_data.get('max_students')

        if min_students and max_students:
            if min_students > max_students:
                raise ValidationError("Minimum students cannot be greater than maximum students")

        return cleaned_data


class AddStudentForm(forms.Form):
    """Form for adding a student to a group"""

    student = forms.ModelChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select Student'
    )

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

        if group:
            # Exclude students already in this group or any other active group
            existing_student_ids = GroupMembership.objects.filter(
                is_active=True
            ).values_list('student_id', flat=True)

            self.fields['student'].queryset = User.objects.filter(
                role='student',
                is_active=True
            ).exclude(id__in=existing_student_ids)

        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username}) - {obj.department or 'No Dept'}"


class BulkAddStudentsForm(forms.Form):
    """Form for adding multiple students to a group at once"""

    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label='Select Students'
    )

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

        if group:
            # Exclude students already in any active group
            existing_student_ids = GroupMembership.objects.filter(
                is_active=True
            ).values_list('student_id', flat=True)

            self.fields['students'].queryset = User.objects.filter(
                role='student',
                is_active=True
            ).exclude(id__in=existing_student_ids)

    def clean_students(self):
        students = self.cleaned_data.get('students')
        if not students:
            raise ValidationError("Please select at least one student")
        return students


class GroupFilterForm(forms.Form):
    """Form for filtering groups"""

    batch_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Batch Year'}),
        label='Batch Year'
    )
    supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(role='supervisor', is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Supervisor'
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('full', 'Full'),
            ('needs_students', 'Needs Students'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Status'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supervisor'].label_from_instance = lambda obj: f"{obj.get_full_name()}"
