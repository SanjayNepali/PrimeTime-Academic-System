# File: Desktop/Prime/chat/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import ChatRoom, ChatRoomMember, Message, MessageReaction, TypingIndicator, ChatNotification


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'room_type', 'group_link', 'participant_count',
        'message_count_display', 'is_active_badge', 'is_frozen_badge',
        'last_message_at', 'created_at'
    ]
    list_filter = ['room_type', 'is_active', 'is_frozen', 'created_at']
    search_fields = ['name', 'group__name']
    readonly_fields = ['created_at', 'updated_at', 'last_message_at']
    filter_horizontal = ['participants']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Room Information', {
            'fields': ('name', 'room_type', 'group', 'participants')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_frozen')
        }),
        ('Schedule', {
            'fields': ('schedule_start_time', 'schedule_end_time', 'schedule_days'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
    )
    
    def group_link(self, obj):
        if obj.group:
            return format_html('<a href="/admin/groups/group/{}/change/">{}</a>', obj.group.id, obj.group.name)
        return '—'
    group_link.short_description = 'Group'
    
    def participant_count(self, obj):
        count = obj.participants.count()
        return format_html('<span class="badge bg-primary">{}</span>', count)
    participant_count.short_description = 'Participants'
    
    def message_count_display(self, obj):
        count = obj.message_count
        return format_html('<span style="color: #007bff;">💬 {}</span>', count)
    message_count_display.short_description = 'Messages'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #6c757d;">✗ Inactive</span>')
    is_active_badge.short_description = 'Active'
    
    def is_frozen_badge(self, obj):
        if obj.is_frozen:
            return format_html('<span style="color: #dc3545;">🔒 Frozen</span>')
        return format_html('<span style="color: #28a745;">🔓 Open</span>')
    is_frozen_badge.short_description = 'Access'


@admin.register(ChatRoomMember)
class ChatRoomMemberAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'room_name', 'is_active', 'is_online_badge', 'last_seen_at', 'joined_at']
    list_filter = ['is_active', 'is_online', 'notifications_enabled', 'joined_at']
    search_fields = ['user__username', 'user__full_name', 'room__name']
    readonly_fields = ['joined_at', 'last_seen_at', 'last_read_at']
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Room'
    
    def is_online_badge(self, obj):
        if obj.is_online:
            return format_html('<span style="color: #28a745;">● Online</span>')
        return format_html('<span style="color: #6c757d;">○ Offline</span>')
    is_online_badge.short_description = 'Status'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'sender_name', 'room_name', 'content_preview', 'message_type',
        'sentiment_display', 'is_flagged_badge', 'is_deleted_badge',
        'read_count_display', 'timestamp'
    ]
    list_filter = ['message_type', 'is_flagged', 'is_deleted', 'timestamp']
    search_fields = ['sender__username', 'sender__full_name', 'content', 'room__name']
    readonly_fields = ['timestamp', 'edited_at', 'deleted_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('room', 'sender', 'message_type', 'content', 'attachment')
        }),
        ('Thread', {
            'fields': ('reply_to',)
        }),
        ('Analysis', {
            'fields': ('sentiment_score', 'is_flagged', 'flag_reason')
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at', 'edited_at')
        }),
        ('Engagement', {
            'fields': ('read_by',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def sender_name(self, obj):
        return obj.sender.display_name
    sender_name.short_description = 'Sender'
    sender_name.admin_order_field = 'sender__full_name'
    
    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Room'
    
    def content_preview(self, obj):
        content = obj.display_content
        if len(content) > 50:
            return content[:50] + '...'
        return content
    content_preview.short_description = 'Content'
    
    def sentiment_display(self, obj):
        score = obj.sentiment_score
        if score > 0.3:
            color = '#28a745'
            icon = '😊'
        elif score < -0.3:
            color = '#dc3545'
            icon = '😞'
        else:
            color = '#ffc107'
            icon = '😐'
        return format_html(
            '<span style="color: {};">{} {:.2f}</span>',
            color, icon, score
        )
    sentiment_display.short_description = 'Sentiment'
    
    def is_flagged_badge(self, obj):
        if obj.is_flagged:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠️ Flagged</span>')
        return format_html('<span style="color: #6c757d;">—</span>')
    is_flagged_badge.short_description = 'Flagged'
    
    def is_deleted_badge(self, obj):
        if obj.is_deleted:
            return format_html('<span style="color: #dc3545;">🗑️ Deleted</span>')
        return format_html('<span style="color: #28a745;">✓ Active</span>')
    is_deleted_badge.short_description = 'Status'
    
    def read_count_display(self, obj):
        count = obj.read_count
        return format_html('<span style="color: #007bff;">👁 {}</span>', count)
    read_count_display.short_description = 'Read By'
    
    actions = ['flag_messages', 'unflag_messages', 'delete_messages']
    
    def flag_messages(self, request, queryset):
        updated = queryset.update(is_flagged=True, flag_reason='Flagged by admin')
        self.message_user(request, f'{updated} message(s) flagged')
    flag_messages.short_description = "Flag selected messages"
    
    def unflag_messages(self, request, queryset):
        updated = queryset.update(is_flagged=False, flag_reason='')
        self.message_user(request, f'{updated} message(s) unflagged')
    unflag_messages.short_description = "Unflag selected messages"
    
    def delete_messages(self, request, queryset):
        for message in queryset:
            message.soft_delete()
        self.message_user(request, f'{queryset.count()} message(s) deleted')
    delete_messages.short_description = "Delete selected messages"


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'message_preview', 'emoji', 'created_at']
    list_filter = ['emoji', 'created_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['created_at']
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def message_preview(self, obj):
        content = obj.message.display_content
        if len(content) > 30:
            return content[:30] + '...'
        return content
    message_preview.short_description = 'Message'


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'notification_type', 'room_name', 'is_read_badge', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'room__name']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Room'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #28a745;">✓ Read</span>')
        return format_html('<span style="color: #dc3545;">✗ Unread</span>')
    is_read_badge.short_description = 'Status'
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        for notification in queryset:
            notification.mark_as_read()
        self.message_user(request, f'{queryset.count()} notification(s) marked as read')
    mark_as_read.short_description = "Mark as read"