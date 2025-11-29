# File: Desktop/Prime/accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import csv
from io import TextIOWrapper
from analytics.utils import log_user_created, log_user_login

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
            
            # Log significant login (first login or admin/supervisor)
            if not user.password_changed or user.role in ['admin', 'supervisor']:
                log_user_login(user)
            
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

    is_forced = request.user.must_change_password

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
    
    # SIMPLE LOGIC: Only set default batch if NO URL parameters exist
    current_active_batch = 2079
    show_default_batch = False
    
    # If no GET parameters at all, it's the first page load
    if not request.GET:
        batch_filter = str(current_active_batch)
        show_default_batch = True
    
    # Build query - exclude superuser from list
    users = User.objects.exclude(is_superuser=True)
    
    # Apply filters
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Only apply batch filter if it has a value AND it's not empty string
    if batch_filter and batch_filter.strip():
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
        'batch_filter': batch_filter or '',
        'status_filter': status_filter,
        'search_query': search_query,
        'roles': User.ROLE_CHOICES,
        'batches': range(2079, 2090),
        'status_choices': [
            ('', 'All Status'),
            ('pending', 'Pending Password Change'),
            ('active', 'Active'),
            ('disabled', 'Disabled')
        ],
        'current_active_batch': current_active_batch,
        'show_default_batch': show_default_batch,
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
            
            # Log user creation activity
            log_user_created(request.user, user)
            
            messages.success(
                request,
                f'User {user.display_name} created successfully! '
                f'Initial password: {initial_password}'
            )
            return redirect('accounts:user_list')

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


@login_required
def user_detail(request, pk):
    """View detailed user information"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    viewed_user = get_object_or_404(User, pk=pk)
    
    # Get project count if user is a student
    project_count = 0
    if viewed_user.is_student:
        pass
    
    context = {
        'viewed_user': viewed_user,
        'project_count': project_count,
        'title': f'{viewed_user.display_name} - User Details'
    }
    return render(request, 'accounts/user_detail.html', context)


@login_required
def password_reset_success(request, pk):
    """Display generated password after successful reset"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    target_user = get_object_or_404(User, pk=pk)
    
    # Get the new password from session (set during password reset)
    new_password = request.session.get(f'new_password_{pk}')
    
    if not new_password:
        messages.error(request, 'Password information not found.')
        return redirect('accounts:user_list')
    
    # Clear the password from session after displaying
    del request.session[f'new_password_{pk}']
    
    context = {
        'target_user': target_user,
        'new_password': new_password,
        'title': 'Password Reset Successful'
    }
    return render(request, 'accounts/password_reset_success.html', context)


@login_required
def user_reset_password_confirm(request, pk):
    """Confirmation page before resetting user password"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    target_user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        # Generate new password
        new_password = target_user.generate_initial_password()
        target_user.set_password(new_password)
        target_user.password_changed = False
        target_user.must_change_password = True
        target_user.initial_password_visible = True
        target_user.password_changed_at = None
        target_user.save()
        
        # Store password in session temporarily
        request.session[f'new_password_{pk}'] = new_password
        
        messages.success(request, f'Password reset for {target_user.display_name}.')
        return redirect('accounts:password_reset_success', pk=pk)
    
    context = {
        'target_user': target_user,
        'title': f'Reset Password - {target_user.display_name}'
    }
    return render(request, 'accounts/user_password_reset_confirm.html', context)


@login_required
def user_disable_confirm(request, pk):
    """Confirmation page before disabling user account"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    target_user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        target_user.is_enabled = False
        target_user.save()
        
        messages.success(request, f'Account disabled for {target_user.display_name}.')
        return redirect('accounts:user_detail', pk=pk)
    
    context = {
        'target_user': target_user,
        'title': f'Disable Account - {target_user.display_name}'
    }
    return render(request, 'accounts/user_disable_confirm.html', context)


@login_required
def user_enable_confirm(request, pk):
    """Confirmation page before enabling user account"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    target_user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        target_user.is_enabled = True
        target_user.save()
        
        messages.success(request, f'Account enabled for {target_user.display_name}.')
        return redirect('accounts:user_detail', pk=pk)
    
    context = {
        'target_user': target_user,
        'title': f'Enable Account - {target_user.display_name}'
    }
    return render(request, 'accounts/user_enable_confirm.html', context)


@login_required
def user_confirm_delete(request, pk):
    """Confirmation page before deleting user"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    user_to_delete = get_object_or_404(User, pk=pk)
    
    # Prevent deleting yourself or superusers
    if user_to_delete == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:user_list')
    
    if user_to_delete.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts.')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        username = user_to_delete.username
        
        # Delete user (cascade will handle related objects)
        user_to_delete.delete()
        
        messages.success(request, f'User {username} has been permanently deleted.')
        return redirect('accounts:user_list')
    
    context = {
        'user_to_delete': user_to_delete,
        'title': f'Delete User - {user_to_delete.display_name}'
    }
    return render(request, 'accounts/user_confirm_delete.html', context)


@login_required
def bulk_user_import(request):
    """Bulk import users from CSV"""
    
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:home')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('accounts:bulk_user_import')
        
        try:
            # Parse CSV
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(csv_data)
            
            success_count = 0
            error_count = 0
            skipped_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Check required fields
                        required_fields = ['user_id', 'email', 'full_name', 'role', 'department']
                        missing_fields = [f for f in required_fields if not row.get(f)]
                        
                        if missing_fields:
                            errors.append(f"Row {row_num}: Missing fields: {', '.join(missing_fields)}")
                            error_count += 1
                            continue
                        
                        # Check if user exists
                        if User.objects.filter(email=row['email']).exists():
                            skipped_count += 1
                            continue
                        
                        if User.objects.filter(user_id=row['user_id']).exists():
                            skipped_count += 1
                            continue
                        
                        # Create username from email
                        username = row['email'].split('@')[0]
                        base_username = username
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1
                        
                        # Create user
                        user = User(
                            username=username,
                            user_id=row['user_id'],
                            email=row['email'],
                            full_name=row['full_name'],
                            role=row['role'],
                            department=row['department'],
                            batch_year=row.get('batch_year') or None,
                            phone=row.get('phone', ''),
                            created_by=request.user
                        )
                        
                        # Generate and set password
                        initial_password = user.generate_initial_password()
                        user.set_password(initial_password)
                        user.must_change_password = True
                        user.save()
                        
                        # Create profile
                        UserProfile.objects.create(user=user)
                        
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            # Return JSON response for AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success_count': success_count,
                    'error_count': error_count,
                    'skipped_count': skipped_count,
                    'errors': errors[:10]
                })
            
            # Regular response
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} users.')
            if skipped_count > 0:
                messages.warning(request, f'Skipped {skipped_count} duplicate users.')
            if error_count > 0:
                messages.error(request, f'{error_count} users failed to import.')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
        
        return redirect('accounts:bulk_user_import')
    
    # Get statistics
    total_users = User.objects.exclude(is_superuser=True).count()
    active_users = User.objects.filter(is_enabled=True, password_changed=True).exclude(is_superuser=True).count()
    disabled_users = User.objects.filter(is_enabled=False).count()
    pending_password = User.objects.filter(password_changed=False).count()
    
    context = {
        'title': 'Bulk User Management',
        'total_users': total_users,
        'active_users': active_users,
        'disabled_users': disabled_users,
        'pending_password': pending_password,
    }
    return render(request, 'accounts/bulk_user_management.html', context)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip