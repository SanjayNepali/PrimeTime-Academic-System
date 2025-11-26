# File: Desktop/Prime/accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from .forms import (
    RoleBasedAuthenticationForm, PasswordChangeForm,
    ProfileUpdateForm, UserCreationByIDForm,
    StudentProfileForm, SupervisorProfileForm, UserUpdateForm
)
from .models import User, UserProfile, LoginHistory, UniversityDatabase


def custom_login(request):
    """Custom login view with role-based authentication"""
    
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = RoleBasedAuthenticationForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Prevent disabled accounts (except superusers)
            if not user.is_enabled and not user.is_superuser:
                messages.error(request, 'Your account has been disabled. Please contact administrator.')
                return render(request, 'accounts/login.html', {'form': form})
            
            # Log the login attempt
            LoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
            
            # Update last login
            user.last_login_at = timezone.now()
            
            # Hide initial password after first login
            if user.initial_password_visible and user.password_changed:
                user.initial_password_visible = False
            
            user.save()
            
            # Set session role
            selected_role = form.cleaned_data['role']
            request.session['active_role'] = selected_role
            
            # Log in the user
            login(request, user)
            messages.success(request, f'Welcome back, {user.display_name}!')
            
            # Force password change for first-time users
            if user.must_change_password and not user.is_superuser:
                messages.info(request, 'Please change your initial password.')
                return redirect('accounts:change_password')
            
            # Redirect to dashboard
            return redirect('dashboard:home')
    else:
        form = RoleBasedAuthenticationForm()
    
    context = {
        'form': form,
        'title': 'Login to PrimeTime'
    }
    return render(request, 'accounts/login.html', context)


@login_required
def custom_logout(request):
    """Logout view"""
    if hasattr(request.user, 'profile'):
        request.user.profile.set_offline()
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')

@login_required
def change_password(request):
    """Password change view — final fixed version (supports forced mode)."""
    print(f"DEBUG: change_password view called - user: {request.user.username}")
    print(f"DEBUG: User must_change_password (before): {request.user.must_change_password}")

    is_forced = request.user.must_change_password  # detect forced password change

    if request.method == "POST":
        # ✅ Pass the forced flag into the form
        form = PasswordChangeForm(request.user, request.POST, is_forced=is_forced)
        if form.is_valid():
            form.save()
            request.user.refresh_from_db()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed successfully!")

            print(f"DEBUG: Password change SUCCESS for user: {request.user.username}")
            print(f"DEBUG: must_change_password (after save): {request.user.must_change_password}")
            print(f"DEBUG: password_changed (after save): {request.user.password_changed}")
            return redirect("dashboard:home")
        else:
            print(f"DEBUG: Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user, is_forced=is_forced)

    context = {
        "form": form,
        "title": "Change Password - PrimeTime",
        "is_forced": is_forced,
    }
    return render(request, "accounts/change_password.html", context)

# ... rest of your views.py remains the same ...
@login_required
def profile_view(request):
    """View user profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': profile,
        'title': 'My Profile - PrimeTime'
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update(request):
    """Update user profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # Select appropriate form based on role
    if request.user.is_student:
        form_class = StudentProfileForm
    elif request.user.is_supervisor:
        form_class = SupervisorProfileForm
    else:
        form_class = ProfileUpdateForm
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = form_class(instance=profile)
    
    context = {
        'form': form,
        'title': 'Update Profile - PrimeTime'
    }
    return render(request, 'accounts/profile_update.html', context)


@login_required
def user_list(request):
    """List all users (for admin only)"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    # Get filter parameters
    role_filter = request.GET.get('role', '')
    batch_filter = request.GET.get('batch', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    # Build query - exclude superuser from list
    users = User.objects.exclude(is_superuser=True)
    
    if role_filter:
        users = users.filter(role=role_filter)
    if batch_filter:
        users = users.filter(batch_year=batch_filter)
    if status_filter == 'pending':
        users = users.filter(password_changed=False)
    elif status_filter == 'active':
        users = users.filter(password_changed=True, is_enabled=True)
    elif status_filter == 'disabled':
        users = users.filter(is_enabled=False)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(user_id__icontains=search_query) |
            Q(department__icontains=search_query)
        )
    
    context = {
        'users': users,
        'title': 'User Management - PrimeTime',
        'role_filter': role_filter,
        'batch_filter': batch_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'roles': User.ROLE_CHOICES,
        'batches': range(2079, 2090),
        'status_choices': [
            ('', 'All Status'),
            ('pending', 'Pending Password Change'),
            ('active', 'Active'),
            ('disabled', 'Disabled')
        ]
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
def create_user(request):
    """Create new user using university ID lookup"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserCreationByIDForm(request.POST)
        if form.is_valid():
            user, initial_password = form.save(created_by=request.user)
            messages.success(
                request,
                f'User {user.display_name} created successfully! '
                f'Initial password: {initial_password}'
            )
            return redirect('accounts:user_list')
    else:
        form = UserCreationByIDForm()
    
    context = {
        'form': form,
        'title': 'Create New User - PrimeTime'
    }
    return render(request, 'accounts/create_user.html', context)


@login_required
def lookup_user_by_id(request):
    """AJAX endpoint to lookup user in university database"""
    
    if not request.user.is_admin:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return JsonResponse({'error': 'User ID required'}, status=400)
    
    # Check if user already exists in system
    if User.objects.filter(user_id=user_id).exists():
        return JsonResponse({'error': 'User already exists in system'}, status=400)
    
    try:
        data = UniversityDatabase.objects.get(user_id=user_id)
        return JsonResponse({
            'success': True,
            'data': {
                'full_name': data.full_name,
                'email': data.email,
                'department': data.department,
                'role': data.role,
                'role_display': data.get_role_display(),
                'enrollment_year': data.enrollment_year,
                'phone': data.phone
            }
        })
    except UniversityDatabase.DoesNotExist:
        return JsonResponse({'error': 'User not found in university database'}, status=404)


@login_required
def user_toggle_status(request, pk):
    """Enable/disable user account"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent self-disabling
    if user == request.user:
        messages.error(request, 'You cannot disable your own account.')
        return redirect('accounts:user_list')
    
    user.is_enabled = not user.is_enabled
    user.save()
    
    action = "enabled" if user.is_enabled else "disabled"
    messages.success(request, f'User {user.display_name} has been {action}.')
    
    return redirect('accounts:user_list')


@login_required
def user_reset_password(request, pk):
    """Reset user password to initial"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, pk=pk)
    
    # Generate new initial password
    new_password = user.generate_initial_password()
    user.set_password(new_password)
    user.password_changed = False
    user.must_change_password = True
    user.initial_password_visible = True
    user.password_changed_at = None
    user.save()
    
    messages.success(
        request,
        f'Password reset for {user.display_name}. '
        f'New initial password: {new_password}'
    )
    
    return redirect('accounts:user_list')


@login_required
def user_update(request, pk):
    """Update user details"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.display_name} updated successfully.')
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'title': f'Update User - {user.display_name}'
    }
    return render(request, 'accounts/user_update.html', context)


@login_required
def login_history(request):
    """View user's login history"""
    
    login_history = LoginHistory.objects.filter(user=request.user).order_by('-login_time')[:50]
    
    context = {
        'login_history': login_history,
        'title': 'Login History - PrimeTime'
    }
    return render(request, 'accounts/login_history.html', context)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip