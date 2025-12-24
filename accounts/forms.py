# File: accounts/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm as DjangoPasswordChangeForm
from django.core.exceptions import ValidationError
from .models import User, UserProfile, UniversityDatabase


class RoleBasedAuthenticationForm(forms.Form):
    """Custom authentication form with role selection"""
    
    identifier = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        label='Password'
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Login As'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None
    
    def clean(self):
        identifier = self.cleaned_data.get('identifier')
        password = self.cleaned_data.get('password')
        role = self.cleaned_data.get('role')
        
        if identifier and password and role:
            # Try to find user by username or email
            try:
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                raise ValidationError("Invalid username/email or password")
            
            # Check password
            if not user.check_password(password):
                raise ValidationError("Invalid username/email or password")
            
            # Check role match
            if user.role != role and not user.is_superuser:
                raise ValidationError(f"You are not registered as a {role}")
            
            # Check if account is enabled
            if not user.is_enabled and not user.is_superuser:
                raise ValidationError("Your account has been disabled")
            
            self.user_cache = user
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache


class PasswordChangeForm(DjangoPasswordChangeForm):
    """Custom password change form"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        }),
        label='Current Password',
        required=False  # Not required for forced changes
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        }),
        label='New Password'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        }),
        label='Confirm New Password'
    )
    
    def __init__(self, user, *args, is_forced=False, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.is_forced = is_forced
        
        # If forced password change, old password not required
        if is_forced:
            self.fields['old_password'].required = False
            self.fields['old_password'].widget = forms.HiddenInput()
    
    def clean_old_password(self):
        """Skip old password validation if forced change"""
        if self.is_forced:
            return ''
        return super().clean_old_password()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.mark_password_changed()
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Base profile update form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio', 'department']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['phone'].initial = self.instance.user.phone
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user fields
        user = profile.user
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.phone = self.cleaned_data['phone']
        
        if commit:
            user.save()
            profile.save()
        
        return profile


class StudentProfileForm(ProfileUpdateForm):
    """Profile form specific to students"""
    
    student_id = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    enrollment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    
    class Meta(ProfileUpdateForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['student_id', 'enrollment_date']
        widgets = {
            **ProfileUpdateForm.Meta.widgets,
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'enrollment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class SupervisorProfileForm(ProfileUpdateForm):
    """Profile form specific to supervisors with schedule settings"""
    
    specialization = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    max_groups = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        required=False
    )
    
    # ============================================
    # NEW: SCHEDULE FIELDS FOR SUPERVISORS
    # ============================================
    schedule_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Enable Time Restrictions',
        help_text='When enabled, students can only message you during specified hours'
    )
    schedule_start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label='Start Time',
        help_text='Time when students can start messaging'
    )
    schedule_end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label='End Time',
        help_text='Time when students must stop messaging'
    )
    schedule_days = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mon,Tue,Wed,Thu,Fri'
        }),
        label='Available Days',
        help_text='Comma-separated days (e.g., Mon,Tue,Wed,Thu,Fri)'
    )
    
    class Meta(ProfileUpdateForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['specialization', 'max_groups']
        widgets = {
            **ProfileUpdateForm.Meta.widgets,
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'max_groups': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            # Load schedule fields from User model
            self.fields['schedule_enabled'].initial = self.instance.user.schedule_enabled
            self.fields['schedule_start_time'].initial = self.instance.user.schedule_start_time
            self.fields['schedule_end_time'].initial = self.instance.user.schedule_end_time
            self.fields['schedule_days'].initial = self.instance.user.schedule_days
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate schedule times if enabled
        if cleaned_data.get('schedule_enabled'):
            start_time = cleaned_data.get('schedule_start_time')
            end_time = cleaned_data.get('schedule_end_time')
            
            if not start_time or not end_time:
                raise ValidationError('Start time and end time are required when schedule is enabled')
            
            if start_time >= end_time:
                raise ValidationError('Start time must be before end time')
        
        return cleaned_data
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user schedule fields
        user = profile.user
        user.schedule_enabled = self.cleaned_data.get('schedule_enabled', False)
        user.schedule_start_time = self.cleaned_data.get('schedule_start_time')
        user.schedule_end_time = self.cleaned_data.get('schedule_end_time')
        user.schedule_days = self.cleaned_data.get('schedule_days', '')
        
        if commit:
            user.save()
            profile.save()
        
        return profile


class UserCreationByIDForm(forms.Form):
    """Form to create user by looking up university ID"""
    
    user_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter University ID'
        }),
        label='University ID'
    )
    batch_year = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Batch Year'
        }),
        required=False,
        label='Batch Year (Optional)'
    )
    
    def clean_user_id(self):
        user_id = self.cleaned_data['user_id']
        
        # Check if user already exists
        if User.objects.filter(user_id=user_id).exists():
            raise ValidationError('A user with this ID already exists in the system')
        
        # Check if ID exists in university database
        try:
            self.university_entry = UniversityDatabase.objects.get(user_id=user_id)
        except UniversityDatabase.DoesNotExist:
            raise ValidationError('This ID was not found in the university database')
        
        return user_id
    
    def save(self, created_by=None):
        """Create user from university database entry"""
        user = self.university_entry.create_user_from_entry(created_by=created_by)
        
        # Set batch year if provided
        batch_year = self.cleaned_data.get('batch_year')
        if batch_year:
            user.batch_year = batch_year
            user.save()
        
        return user, user.initial_password


class UserUpdateForm(forms.ModelForm):
    """Form for updating existing user details"""
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'department', 'role', 'batch_year', 'is_enabled']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'batch_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }