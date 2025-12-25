# File: groups/forms.py - IMPROVED VERSION

from django import forms
from django.core.exceptions import ValidationError
from .models import Group, GroupMembership
from .utils import get_current_batch_year, get_batch_year_choices
from accounts.models import User


class GroupForm(forms.ModelForm):
    """Form for creating and editing groups with improved defaults"""
    
    # Optional: Add students during creation
    add_students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Add Students (Optional)',
        help_text='You can add students now or later'
    )

    class Meta:
        model = Group
        fields = ['name', 'supervisor', 'batch_year', 'min_students', 'max_students', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Group A',
                'required': True
            }),
            'supervisor': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'batch_year': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'min_students': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'max': 10,
                'value': 5
            }),
            'max_students': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'max': 10,
                'value': 7
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'checked': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set batch year choices
        self.fields['batch_year'].widget = forms.Select(
            choices=get_batch_year_choices(),
            attrs={'class': 'form-control', 'required': True}
        )
        
        # Set initial batch year to current
        if not self.instance.pk:  # Only for new groups
            self.fields['batch_year'].initial = get_current_batch_year()
            self.fields['min_students'].initial = 5
            self.fields['max_students'].initial = 7
            self.fields['is_active'].initial = True
        
        # Only show supervisors
        self.fields['supervisor'].queryset = User.objects.filter(
            role='supervisor', 
            is_active=True
        ).order_by('first_name', 'last_name')
        
        self.fields['supervisor'].label_from_instance = lambda obj: (
            f"{obj.display_name} ({obj.email})"
        )
        
        # Setup add_students field
        if not self.instance.pk:  # Only for creation
            existing_student_ids = GroupMembership.objects.filter(
                is_active=True
            ).values_list('student_id', flat=True)
            
            self.fields['add_students'].queryset = User.objects.filter(
                role='student',
                is_active=True
            ).exclude(id__in=existing_student_ids).order_by('first_name', 'last_name')
            
            self.fields['add_students'].label_from_instance = lambda obj: (
                f"{obj.display_name} - {obj.department or 'No Dept'}"
            )
        else:
            # Remove add_students field when editing
            del self.fields['add_students']

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        batch_year = cleaned_data.get('batch_year')
        supervisor = cleaned_data.get('supervisor')
        min_students = cleaned_data.get('min_students')
        max_students = cleaned_data.get('max_students')
        is_active = cleaned_data.get('is_active')
        add_students = cleaned_data.get('add_students', [])
        
        # Validate duplicate group name in same batch year
        if name and batch_year:
            name_clean = name.strip()
            
            if is_active:
                existing_groups = Group.objects.filter(
                    name__iexact=name_clean,
                    batch_year=batch_year,
                    is_active=True
                ).exclude(id=self.instance.pk if self.instance.pk else None)
                
                if existing_groups.exists():
                    raise ValidationError({
                        'name': f'A group named "{name_clean}" already exists in batch year {batch_year}.'
                    })
        
        # Validate supervisor doesn't have another active group in same batch
        if supervisor and batch_year and is_active:
            existing_supervisor_groups = Group.objects.filter(
                supervisor=supervisor,
                batch_year=batch_year,
                is_active=True
            ).exclude(id=self.instance.pk if self.instance.pk else None)
            
            if existing_supervisor_groups.exists():
                existing_group = existing_supervisor_groups.first()
                raise ValidationError({
                    'supervisor': (
                        f'Supervisor "{supervisor.display_name}" already has an active group '
                        f'("{existing_group.name}") in batch year {batch_year}.'
                    )
                })
        
        # Validate min/max students
        if min_students and max_students:
            if min_students > max_students:
                raise ValidationError({
                    'min_students': "Minimum students cannot be greater than maximum students"
                })
            
            if min_students < 1:
                raise ValidationError({
                    'min_students': "Minimum students must be at least 1"
                })
            
            if max_students > 20:
                raise ValidationError({
                    'max_students': "Maximum students cannot exceed 20"
                })
        
        # Validate number of students being added doesn't exceed max
        if add_students and max_students:
            if len(add_students) > max_students:
                raise ValidationError({
                    'add_students': f"Cannot add {len(add_students)} students. Maximum is {max_students}."
                })

        return cleaned_data


class QuickGroupCreateForm(forms.Form):
    """Quick form to create group by assigning supervisor"""
    
    supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(role='supervisor', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label='Select Supervisor'
    )
    
    group_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Group A (optional)',
            'required': False
        }),
        label='Group Name (Optional)',
        required=False,
        help_text='Leave blank to auto-generate (e.g., "Dr. Smith\'s Group")'
    )
    
    batch_year = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Batch Year'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch_year'].choices = get_batch_year_choices()
        self.fields['batch_year'].initial = get_current_batch_year()
        
        self.fields['supervisor'].label_from_instance = lambda obj: (
            f"{obj.display_name} ({obj.email})"
        )
    
    def clean(self):
        cleaned_data = super().clean()
        supervisor = cleaned_data.get('supervisor')
        batch_year = cleaned_data.get('batch_year')
        
        # Check if supervisor already has a group in this batch
        if supervisor and batch_year:
            existing = Group.objects.filter(
                supervisor=supervisor,
                batch_year=batch_year,
                is_active=True
            ).exists()
            
            if existing:
                raise ValidationError(
                    f"Supervisor {supervisor.display_name} already has an active group "
                    f"in batch year {batch_year}"
                )
        
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
            ).exclude(id__in=existing_student_ids).order_by('first_name', 'last_name')

        self.fields['student'].label_from_instance = lambda obj: (
            f"{obj.display_name} ({obj.username}) - {obj.department or 'No Dept'}"
        )


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
            ).exclude(id__in=existing_student_ids).order_by('first_name', 'last_name')
            
            self.fields['students'].label_from_instance = lambda obj: (
                f"{obj.display_name} - {obj.department or 'No Dept'}"
            )

    def clean_students(self):
        students = self.cleaned_data.get('students')
        if not students:
            raise ValidationError("Please select at least one student")
        return students


class GroupFilterForm(forms.Form):
    """Form for filtering groups"""

    batch_year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
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
            ('', 'All Groups'),
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
        
        # Add "All" option and batch year choices
        batch_choices = [('', 'All Batch Years')] + list(get_batch_year_choices())
        self.fields['batch_year'].choices = batch_choices
        
        self.fields['supervisor'].label_from_instance = lambda obj: obj.display_name