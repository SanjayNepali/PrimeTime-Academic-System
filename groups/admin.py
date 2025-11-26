# File: Desktop/Prime/groups/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Group, GroupMembership, GroupActivity


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'supervisor_name', 'batch_year', 
        'student_count_display', 'status_display', 'created_at'
    ]
    list_filter = ['batch_year', 'is_active', 'is_full']
    search_fields = ['name', 'supervisor__username', 'supervisor__first_name', 'supervisor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'batch_year', 'supervisor')
        }),
        ('Settings', {
            'fields': ('min_students', 'max_students', 'is_active', 'is_full')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def supervisor_name(self, obj):
        return obj.supervisor.get_full_name() or obj.supervisor.username
    supervisor_name.short_description = 'Supervisor'
    
    def student_count_display(self, obj):
        count = obj.student_count
        max_students = obj.max_students
        color = '#28a745' if count >= obj.min_students else '#ffc107'
        if count >= max_students:
            color = '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color, count, max_students
        )
    student_count_display.short_description = 'Students'
    
    def status_display(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: #6c757d;">Inactive</span>')
        elif obj.is_full:
            return format_html('<span style="color: #dc3545;">Full</span>')
        elif obj.student_count >= obj.min_students:
            return format_html('<span style="color: #28a745;">Active</span>')
        else:
            return format_html('<span style="color: #ffc107;">Needs Students</span>')
    status_display.short_description = 'Status'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'group_name', 'is_active', 'joined_at', 'left_at']
    list_filter = ['is_active', 'joined_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'group__name']
    readonly_fields = ['joined_at']
    
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username
    student_name.short_description = 'Student'
    
    def group_name(self, obj):
        return obj.group.name
    group_name.short_description = 'Group'


@admin.register(GroupActivity)
class GroupActivityAdmin(admin.ModelAdmin):
    list_display = ['group', 'action', 'user', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['group__name', 'user__username', 'details']
    readonly_fields = ['group', 'user', 'action', 'details', 'timestamp']
    
    def has_add_permission(self, request):
        return False