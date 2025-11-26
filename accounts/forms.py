# File: Desktop/Prime/accounts/forms.py

from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm,
    PasswordChangeForm as BasePasswordChangeForm
)
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User, UserProfile, UniversityDatabase
from django.db import transaction

class RoleBasedAuthenticationForm(forms.Form):
    """Login form that allows login using Email or Student ID with role verification"""

    identifier = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email or Student ID',
            'autofocus': True
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    role = forms.ChoiceField(
        choices=[('', 'Select Your Role')] + User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )

    def clean(self):
        identifier = self.cleaned_data.get('identifier')
        password = self.cleaned_data.get('password')
        role = self.cleaned_data.get('role')

        if not (identifier and password and role):
            raise ValidationError("Please fill all required fields.")

        user = None

        # 1️⃣ Try matching by email
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            pass

        # 2️⃣ If not found, try matching by student_id (in UserProfile)
        if user is None:
            try:
                user = User.objects.get(profile__student_id__iexact=identifier)
            except User.DoesNotExist:
                raise ValidationError("No account found with this email or student ID.")

        # 3️⃣ Authenticate using username
        self.user_cache = authenticate(username=user.username, password=password)
        if self.user_cache is None:
            raise ValidationError("Invalid password.")

        # 4️⃣ Role validation
        if self.user_cache.is_superuser and role == 'admin':
            pass
        elif self.user_cache.role != role:
            raise ValidationError(f"You are not authorized to login as {role}.")

        # 5️⃣ Account state checks
        if not self.user_cache.is_active:
            raise ValidationError("This account is inactive.")
        if not self.user_cache.is_enabled:
            raise ValidationError("This account has been disabled.")

        return self.cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)

class UserCreationByIDForm(forms.Form):
    """Form for creating users by university ID lookup"""
    
    user_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter University ID (e.g., STU2025001)',
            'id': 'user-id-input'
        })
    )
    
    # Auto-populated fields
    full_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}))
    department = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}))
    role = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}))
    enrollment_year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}))
    
    def clean_user_id(self):
        user_id = self.cleaned_data.get('user_id')
        
        if User.objects.filter(user_id=user_id).exists():
            raise ValidationError(f"User with ID {user_id} already exists in the system")
        
        try:
            self.university_data = UniversityDatabase.objects.get(user_id=user_id)
        except UniversityDatabase.DoesNotExist:
            raise ValidationError(f"No user found with ID {user_id} in university database")
        
        return user_id
    

    def save(self, created_by=None):
        """Create user from university database safely"""
        if not hasattr(self, 'university_data'):
            return None

        data = self.university_data
        username = data.email.split('@')[0] if data.email else data.user_id.lower()
        
        # Ensure username uniqueness
        base_username, counter = username, 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        with transaction.atomic():
            user = User(
                username=username,
                user_id=data.user_id,
                email=data.email,
                full_name=data.full_name,
                department=data.department,
                role=data.role,
                enrollment_year=data.enrollment_year,
                phone=data.phone,
                created_by=created_by
            )

            # Generate and set initial password
            initial_password = user.generate_initial_password()
            user.set_password(initial_password)
            user.must_change_password = True
            user.initial_password_visible = True
            user.save()

            # Create profile
            UserProfile.objects.get_or_create(user=user)

        # Return user and initial password
        return user, initial_password


class UserRegistrationForm(UserCreationForm):
    """Form for admin to create new users manually"""
    
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    batch_year = forms.ChoiceField(choices=[('', 'Select Batch Year')] + [(year, str(year)) for year in range(2079, 2090)], required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    user_id = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University ID (optional)'}))
    full_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    department = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'user_id', 'role', 'department', 'batch_year', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password fields - we'll generate it
        if 'password1' in self.fields:
            del self.fields['password1']
        if 'password2' in self.fields:
            del self.fields['password2']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    
    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.created_by = created_by
        
        # Generate initial password
        initial_password = user.generate_initial_password()
        user.set_password(initial_password)
        user.must_change_password = True
        user.password_changed = False
        
        if commit:
            user.save()
            UserProfile.objects.create(user=user)
            
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Enhanced login form with better styling"""
    
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    
    def clean_username(self):
        """Allow login with email or username"""
        username = self.cleaned_data.get('username')
        
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                pass
        
        return username
    
    def clean(self):
        """Populate auto-fill fields for admin preview"""
        cleaned_data = super().clean()
        if hasattr(self, 'university_data'):
            data = self.university_data
            cleaned_data['full_name'] = data.full_name
            cleaned_data['email'] = data.email
            cleaned_data['department'] = data.department
            cleaned_data['role'] = data.role
            cleaned_data['enrollment_year'] = data.enrollment_year
        return cleaned_data

class PasswordChangeForm(BasePasswordChangeForm):
    """Custom password change form — skips old_password for forced users"""

    def __init__(self, user, *args, **kwargs):
        # ✅ Read the forced flag from kwargs
        self.is_forced = kwargs.pop("is_forced", False)
        super().__init__(user, *args, **kwargs)

        # ✅ Remove old password field if forced
        if self.is_forced and "old_password" in self.fields:
            self.fields.pop("old_password")

    def clean_old_password(self):
        # ✅ Skip validation when forced
        if self.is_forced:
            return None
        return super().clean_old_password()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.password_changed = True
            user.must_change_password = False
            user.initial_password_visible = False
            user.password_changed_at = timezone.now()
            user.save()
            print(
                f"PASSWORD CHANGE: User {user.username} updated — must_change_password: {user.must_change_password}"
            )
        return user

class ProfileUpdateForm(forms.ModelForm):
    """Form for users to update their profile"""
    
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    full_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))
    department = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}))
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about yourself...'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['phone'].initial = self.instance.user.phone
            self.fields['department'].initial = self.instance.user.department
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if commit:
            user = profile.user
            user.email = self.cleaned_data['email']
            user.full_name = self.cleaned_data['full_name']
            user.phone = self.cleaned_data['phone']
            user.department = self.cleaned_data['department']
            user.save()
            profile.save()
        
        return profile


class StudentProfileForm(ProfileUpdateForm):
    """Student-specific profile form"""
    
    student_id = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'}))
    enrollment_year = forms.IntegerField(required=False, min_value=2000, max_value=2100, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enrollment Year'}))
    
    class Meta(ProfileUpdateForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['student_id']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['student_id'].initial = self.instance.student_id
            self.fields['enrollment_year'].initial = self.instance.user.enrollment_year
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.student_id = self.cleaned_data['student_id']
        
        if commit:
            profile.user.enrollment_year = self.cleaned_data['enrollment_year']
            profile.user.save()
            profile.save()
        
        return profile


class SupervisorProfileForm(ProfileUpdateForm):
    """Supervisor-specific profile form"""
    
    specialization = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your areas of expertise'}))
    max_groups = forms.IntegerField(required=False, min_value=1, max_value=10, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum groups (1-10)'}))
    
    class Meta(ProfileUpdateForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['specialization', 'max_groups']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['specialization'].initial = self.instance.specialization
            self.fields['max_groups'].initial = self.instance.max_groups
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.specialization = self.cleaned_data['specialization']
        profile.max_groups = self.cleaned_data['max_groups'] or 3
        
        if commit:
            profile.save()
        
        return profile


class UserUpdateForm(forms.ModelForm):
    """Form for admin to update user details"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'user_id', 'role', 'department', 'batch_year', 'phone', 'is_enabled']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_id': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_year': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }