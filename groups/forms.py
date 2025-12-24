# File: groups/forms.py - COMPLETELY FIXED

from django import forms
from django.core.exceptions import ValidationError
from .models import Group, GroupMembership
from accounts.models import User


class GroupForm(forms.ModelForm):
    """Form for creating and editing groups with FIXED validation"""

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
        # Only show supervisors
        self.fields['supervisor'].queryset = User.objects.filter(role='supervisor', is_active=True)
        self.fields['supervisor'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.username})"

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        batch_year = cleaned_data.get('batch_year')
        supervisor = cleaned_data.get('supervisor')
        min_students = cleaned_data.get('min_students')
        max_students = cleaned_data.get('max_students')
        is_active = cleaned_data.get('is_active')
        
        # CRITICAL FIX: Check for duplicate group name in same batch year (case insensitive)
        if name and batch_year:
            name_clean = name.strip()
            
            # Only check for duplicates if the group is active
            if is_active:
                existing_groups = Group.objects.filter(
                    name__iexact=name_clean,
                    batch_year=batch_year,
                    is_active=True
                ).exclude(id=self.instance.pk if self.instance else None)
                
                if existing_groups.exists():
                    raise ValidationError(
                        f'❌ A group named "{name_clean}" already exists in batch year {batch_year}. '
                        'Group names must be unique within the same batch year.'
                    )
        
        # CRITICAL FIX: Validate supervisor doesn't already have active group in same batch
        if supervisor and batch_year and is_active:
            existing_supervisor_groups = Group.objects.filter(
                supervisor=supervisor,
                batch_year=batch_year,
                is_active=True
            ).exclude(id=self.instance.pk if self.instance else None)
            
            if existing_supervisor_groups.exists():
                existing_group = existing_supervisor_groups.first()
                raise ValidationError(
                    f'❌ Supervisor "{supervisor.display_name}" already has an active group '
                    f'("{existing_group.name}") in batch year {batch_year}. '
                    'Each supervisor can only have ONE active group per batch year.'
                )
        
        # Validate min/max students
        if min_students and max_students:
            if min_students > max_students:
                raise ValidationError("❌ Minimum students cannot be greater than maximum students")
            
            if min_students < 1:
                raise ValidationError("❌ Minimum students must be at least 1")
            
            if max_students > 20:
                raise ValidationError("❌ Maximum students cannot exceed 20")

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
            # Exclude students already in any active group
            existing_student_ids = GroupMembership.objects.filter(
                is_active=True
            ).values_list('student_id', flat=True)

            self.fields['student'].queryset = User.objects.filter(
                role='student',
                is_active=True
            ).exclude(id__in=existing_student_ids)

        self.fields['student'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.username}) - {obj.department or 'No Dept'}"


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
            raise ValidationError("❌ Please select at least one student")
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
        self.fields['supervisor'].label_from_instance = lambda obj: f"{obj.display_name}"