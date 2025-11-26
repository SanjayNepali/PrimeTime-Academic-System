# File: Desktop/Prime/projects/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Project, ProjectDeliverable, ProjectActivity


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'student_info', 'status_badge', 'supervisor_info', 
        'progress_bar', 'batch_year', 'created_at'
    ]
    list_filter = ['status', 'batch_year', 'created_at', 'supervisor']
    search_fields = [
        'title', 'student__username', 'student__email', 'student__full_name',
        'student__user_id', 'description', 'programming_languages'
    ]
    readonly_fields = ['progress_percentage', 'created_at', 'updated_at', 'submitted_at']
    list_select_related = ['student', 'supervisor']
    
    fieldsets = (
        ('Project Information', {
            'fields': ('title', 'description', 'programming_languages', 'batch_year')
        }),
        ('People', {
            'fields': ('student', 'supervisor', 'reviewed_by')
        }),
        ('Status', {
            'fields': ('status', 'progress_percentage', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at', 'review_date'),
            'classes': ('collapse',)
        }),
    )
    
    def student_info(self, obj):
        """Enhanced student display with user_id"""
        if obj.student.user_id:
            return f"{obj.student.display_name} ({obj.student.user_id})"
        return obj.student.display_name
    student_info.short_description = 'Student'
    student_info.admin_order_field = 'student__full_name'
    
    def supervisor_info(self, obj):
        """Enhanced supervisor display"""
        if obj.supervisor:
            if obj.supervisor.user_id:
                return f"{obj.supervisor.display_name} ({obj.supervisor.user_id})"
            return obj.supervisor.display_name
        return '-'
    supervisor_info.short_description = 'Supervisor'
    supervisor_info.admin_order_field = 'supervisor__full_name'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#28a745', 
            'rejected': '#dc3545',
            'in_progress': '#17a2b8',
            'completed': '#007bff',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def progress_bar(self, obj):
        color = '#28a745' if obj.progress_percentage >= 70 else '#ffc107' if obj.progress_percentage >= 40 else '#dc3545'
        return format_html(
            '<div style="width: 80px; background-color: #e9ecef; border-radius: 10px; height: 20px; position: relative;">'
            '<div style="width: {}%; background-color: {}; height: 100%; border-radius: 10px; transition: width 0.3s ease;">'
            '</div><span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 10px; font-weight: 600; color: {};">{}%</span></div>',
            obj.progress_percentage, color,
            'white' if obj.progress_percentage > 50 else 'black',
            obj.progress_percentage
        )
    progress_bar.short_description = 'Progress'


@admin.register(ProjectDeliverable)
class ProjectDeliverableAdmin(admin.ModelAdmin):
    list_display = [
        'project_title', 'stage_display', 'approval_status', 'marks', 
        'submitted_at', 'reviewed_at'
    ]
    list_filter = ['stage', 'is_approved', 'submitted_at', 'project__batch_year']
    search_fields = [
        'project__title', 'project__student__username', 
        'project__student__full_name', 'project__student__user_id'
    ]
    readonly_fields = ['submitted_at', 'updated_at', 'reviewed_at']
    list_select_related = ['project', 'project__student']
    
    def project_title(self, obj):
        return obj.project.title
    project_title.short_description = 'Project'
    project_title.admin_order_field = 'project__title'
    
    def stage_display(self, obj):
        return obj.get_stage_display()
    stage_display.short_description = 'Stage'
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: #28a745;">✓ Approved</span>')
        return format_html('<span style="color: #dc3545;">⏳ Pending</span>')
    approval_status.short_description = 'Status'


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ['project_title', 'action_display', 'user_info', 'timestamp_short']
    list_filter = ['action', 'timestamp', 'project__batch_year']
    search_fields = [
        'project__title', 'user__username', 'user__full_name', 
        'user__user_id', 'details'
    ]
    readonly_fields = ['project', 'user', 'action', 'details', 'timestamp']
    list_select_related = ['project', 'user']
    
    def project_title(self, obj):
        return obj.project.title
    project_title.short_description = 'Project'
    
    def action_display(self, obj):
        return obj.get_action_display()
    action_display.short_description = 'Action'
    
    def user_info(self, obj):
        if obj.user:
            return obj.user.display_name
        return 'System'
    user_info.short_description = 'User'
    
    def timestamp_short(self, obj):
        return obj.timestamp.strftime('%b %d, %H:%M')
    timestamp_short.short_description = 'Time'
    timestamp_short.admin_order_field = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return False