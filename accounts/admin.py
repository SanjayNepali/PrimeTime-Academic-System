# File: Desktop/Prime/accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib import messages
from .models import User, UserProfile, UniversityDatabase, LoginHistory


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ['profile_picture', 'bio', 'department', 'student_id', 'specialization', 'max_groups', 'notifications_enabled']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with simplified role system"""
    
    list_display = [
        'username', 'email', 'display_name', 'display_role', 'user_id',
        'batch_year', 'password_status', 'account_status', 'created_at'
    ]
    list_filter = [
        'role', 'password_changed', 'is_enabled', 'initial_password_visible',
        'batch_year', 'department', 'is_staff', 'is_superuser', 'created_at'
    ]
    search_fields = [
        'username', 'email', 'full_name', 'user_id', 
        'first_name', 'last_name', 'department'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_login_at', 'password_changed_at']
    ordering = ['-created_at']
    
    inlines = [UserProfileInline]
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('University Information', {
            'fields': ('user_id', 'full_name', 'department', 'enrollment_year')
        }),
        ('Role & Access', {
            'fields': ('role', 'batch_year', 'is_enabled', 'created_by')
        }),
        ('Password Management', {
            'fields': (
                'initial_password', 'initial_password_visible',
                'password_changed', 'must_change_password', 'password_changed_at'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'role', 'batch_year', 'user_id', 'full_name'
            ),
        }),
    )
    
    def display_role(self, obj):
        """Display role with color coding"""
        colors = {
            'admin': '#dc3545',      # Red
            'supervisor': '#007bff', # Blue
            'student': '#28a745',    # Green
        }
        role_display = 'Admin' if obj.is_superuser else obj.get_role_display()
        color = colors.get(obj.role, '#000')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; border-radius: 4px; background: {}20;">{}</span>',
            color, color, role_display
        )
    display_role.short_description = 'Role'
    display_role.admin_order_field = 'role'
    
    def password_status(self, obj):
        """Show password change status"""
        if obj.password_changed:
            return format_html('<span style="color: green; font-weight: bold;">✓ Changed</span>')
        elif obj.initial_password_visible:
            return format_html('<span style="color: orange; font-weight: bold;">⚠ Initial ({})</span>', obj.initial_password)
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ Must Change</span>')
    password_status.short_description = 'Password'
    
    def account_status(self, obj):
        """Show account enabled status"""
        if obj.is_enabled:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Disabled</span>')
    account_status.short_description = 'Status'
    
    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Display Name'
    display_name.admin_order_field = 'full_name'
    
    actions = ['enable_users', 'disable_users', 'reset_passwords']
    
    def enable_users(self, request, queryset):
        """Enable selected users"""
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f'{updated} users enabled successfully.', messages.SUCCESS)
    enable_users.short_description = "Enable selected users"
    
    def disable_users(self, request, queryset):
        """Disable selected users (excluding current user and superusers)"""
        queryset = queryset.exclude(id=request.user.id).exclude(is_superuser=True)
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f'{updated} users disabled successfully.', messages.SUCCESS)
    disable_users.short_description = "Disable selected users"
    
    def reset_passwords(self, request, queryset):
        """Reset passwords for selected users"""
        for user in queryset:
            if user != request.user:  # Don't reset own password
                new_password = user.generate_initial_password()
                user.set_password(new_password)
                user.password_changed = False
                user.must_change_password = True
                user.initial_password_visible = True
                user.save()
        
        self.message_user(request, f'Passwords reset for {queryset.count()} users.', messages.SUCCESS)
    reset_passwords.short_description = "Reset passwords for selected users"


# Keep UserProfileAdmin, UniversityDatabaseAdmin, and LoginHistoryAdmin the same
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'student_id', 'specialization', 'notifications_enabled', 'is_online', 'last_seen']
    list_filter = ['department', 'notifications_enabled', 'is_online']
    search_fields = ['user__username', 'user__email', 'user__full_name', 'student_id', 'specialization']
    readonly_fields = ['last_seen']


@admin.register(UniversityDatabase)
class UniversityDatabaseAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'full_name', 'email', 'department', 'role', 'enrollment_year']
    list_filter = ['role', 'department', 'enrollment_year']
    search_fields = ['user_id', 'full_name', 'email', 'department']
    readonly_fields = ['user_id', 'full_name', 'email', 'department', 'role', 'enrollment_year', 'phone']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'success_status']
    list_filter = ['success', 'login_time']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'login_time', 'success']
    date_hierarchy = 'login_time'
    
    def success_status(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-weight: bold;">✓ Success</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Failed</span>')
    success_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser