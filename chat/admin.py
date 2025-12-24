# File: Desktop/Prime/chat/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import ChatRoom, ChatRoomMember, Message, MessageReaction, TypingIndicator, ChatNotification, PendingMessage 


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

@admin.register(PendingMessage)
class PendingMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sender_name', 'target_supervisor_name', 'room_name',
        'status_badge', 'content_preview', 'created_at_display',
        'scheduled_delivery_display', 'delivery_countdown'
    ]
    list_filter = ['status', 'created_at', 'scheduled_delivery_time']
    search_fields = [
        'sender__username', 'sender__full_name',
        'target_supervisor__username', 'target_supervisor__full_name',
        'content', 'room__name'
    ]
    readonly_fields = [
        'created_at', 'delivered_at', 'delivered_message',
        'attempts', 'last_attempt_at', 'error_message'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message Details', {
            'fields': ('room', 'sender', 'target_supervisor', 'content', 'attachment')
        }),
        ('Status', {
            'fields': ('status', 'sentiment_score', 'is_flagged')
        }),
        ('Scheduling', {
            'fields': ('scheduled_delivery_time', 'expires_at')
        }),
        ('Delivery Info', {
            'fields': ('delivered_at', 'delivered_message', 'attempts', 'last_attempt_at', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Threading', {
            'fields': ('reply_to',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['deliver_now', 'mark_as_expired', 'recalculate_delivery_time']
    
    def sender_name(self, obj):
        return obj.sender.display_name
    sender_name.short_description = 'Sender'
    sender_name.admin_order_field = 'sender__full_name'
    
    def target_supervisor_name(self, obj):
        return obj.target_supervisor.display_name
    target_supervisor_name.short_description = 'To Supervisor'
    target_supervisor_name.admin_order_field = 'target_supervisor__full_name'
    
    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Room'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#F59E0B',
            'delivered': '#10B981',
            'failed': '#EF4444',
            'expired': '#6B7280'
        }
        color = colors.get(obj.status, '#6B7280')
        
        icons = {
            'pending': '⏳',
            'delivered': '✅',
            'failed': '❌',
            'expired': '⏰'
        }
        icon = icons.get(obj.status, '•')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def content_preview(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + '...'
        return obj.content
    content_preview.short_description = 'Content'
    
    def created_at_display(self, obj):
        from django.utils.timesince import timesince
        return format_html(
            '{}<br><small style="color: #6B7280;">{} ago</small>',
            obj.created_at.strftime('%Y-%m-%d %H:%M'),
            timesince(obj.created_at)
        )
    created_at_display.short_description = 'Created'
    
    def scheduled_delivery_display(self, obj):
        if not obj.scheduled_delivery_time:
            return '—'
        
        from django.utils.timesince import timeuntil
        from django.utils import timezone
        
        if obj.scheduled_delivery_time > timezone.now():
            return format_html(
                '{}<br><small style="color: #10B981;">in {}</small>',
                obj.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
                timeuntil(obj.scheduled_delivery_time)
            )
        else:
            return format_html(
                '{}<br><small style="color: #EF4444;">overdue</small>',
                obj.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M')
            )
    scheduled_delivery_display.short_description = 'Scheduled For'
    
    def delivery_countdown(self, obj):
        if obj.status != 'pending':
            return '—'
        
        if obj.time_until_delivery:
            total_seconds = int(obj.time_until_delivery.total_seconds())
            
            if total_seconds < 0:
                return format_html('<span style="color: #EF4444;">⚠️ Ready to deliver</span>')
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            if hours > 24:
                days = hours // 24
                return format_html('<span style="color: #F59E0B;">{} days</span>', days)
            elif hours > 0:
                return format_html('<span style="color: #F59E0B;">{}h {}m</span>', hours, minutes)
            else:
                return format_html('<span style="color: #10B981;">{}m</span>', minutes)
        
        return '—'
    delivery_countdown.short_description = 'Time Until Delivery'
    
    # ============================================
    # ADMIN ACTIONS
    # ============================================
    
    def deliver_now(self, request, queryset):
        """Manually deliver pending messages"""
        delivered_count = 0
        failed_count = 0
        
        for pending_msg in queryset.filter(status='pending'):
            message = pending_msg.deliver()
            if message:
                delivered_count += 1
            else:
                failed_count += 1
        
        if delivered_count > 0:
            self.message_user(request, f'{delivered_count} message(s) delivered successfully')
        if failed_count > 0:
            self.message_user(request, f'{failed_count} message(s) failed to deliver', level='warning')
    deliver_now.short_description = "✅ Deliver selected messages now"
    
    def mark_as_expired(self, request, queryset):
        """Mark messages as expired"""
        count = queryset.filter(status='pending').update(status='expired')
        self.message_user(request, f'{count} message(s) marked as expired')
    mark_as_expired.short_description = "⏰ Mark as expired"
    
    def recalculate_delivery_time(self, request, queryset):
        """Recalculate delivery times based on current supervisor schedules"""
        updated_count = 0
        
        for pending_msg in queryset.filter(status='pending'):
            new_delivery_time = pending_msg.calculate_delivery_time()
            pending_msg.scheduled_delivery_time = new_delivery_time
            pending_msg.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} delivery time(s) recalculated')
    recalculate_delivery_time.short_description = "🔄 Recalculate delivery times"
