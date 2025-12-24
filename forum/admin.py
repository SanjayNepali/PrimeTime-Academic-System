# File: forum/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import ForumCategory, ForumTag, ForumPost, ForumReply, ForumNotification


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_display', 'color_display', 'order', 'post_count_display', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']
    
    def icon_display(self, obj):
        return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
    icon_display.short_description = 'Icon'
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 50px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'
    
    def post_count_display(self, obj):
        """Display post count"""
        count = obj.forumpost_set.count()
        return format_html('<span class="badge bg-primary">{}</span>', count)
    post_count_display.short_description = 'Posts'


@admin.register(ForumTag)
class ForumTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'post_count_display']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def post_count_display(self, obj):
        """Display post count"""
        count = obj.forumpost_set.count()
        return format_html('<span class="badge bg-primary">{}</span>', count)
    post_count_display.short_description = 'Posts'


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'post_type_badge', 'category', 'author_name',
        'status_badge', 'views_count', 'reply_count_display', 
        'upvote_count_display', 'is_flagged_badge', 'created_at'
    ]
    list_filter = [
        'post_type', 'status', 'is_solved', 'is_pinned', 
        'is_flagged', 'is_hidden', 'category', 'created_at'
    ]
    search_fields = ['title', 'content', 'author__username', 'author__full_name']
    readonly_fields = ['views', 'created_at', 'updated_at', 'last_activity']
    filter_horizontal = ['tags', 'upvotes', 'followers']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Post Information', {
            'fields': ('title', 'content', 'post_type', 'category', 'author')
        }),
        ('Status', {
            'fields': ('status', 'is_solved', 'solved_by', 'is_pinned')
        }),
        ('Classification', {
            'fields': ('tags', 'programming_languages')
        }),
        ('Engagement', {
            'fields': ('views', 'upvotes', 'followers'),
            'classes': ('collapse',)
        }),
        ('Moderation', {
            'fields': ('is_flagged', 'flag_reason', 'flagged_by', 'is_hidden'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def author_name(self, obj):
        return obj.author.display_name
    author_name.short_description = 'Author'
    author_name.admin_order_field = 'author__full_name'
    
    def post_type_badge(self, obj):
        colors = {
            'question': '#007bff',
            'discussion': '#28a745',
            'help': '#ffc107',
            'announcement': '#dc3545',
            'tutorial': '#17a2b8',
            'showcase': '#6f42c1'
        }
        color = colors.get(obj.post_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, obj.get_post_type_display().upper()
        )
    post_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'open': '#28a745',
            'solved': '#007bff',
            'closed': '#6c757d',
            'pinned': '#ffc107'
        }
        color = colors.get(obj.status, '#6c757d')
        icon = '📌' if obj.is_pinned else '✓' if obj.is_solved else '○'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def views_count(self, obj):
        return format_html('<span style="color: #007bff;">👁 {}</span>', obj.views)
    views_count.short_description = 'Views'
    views_count.admin_order_field = 'views'
    
    def reply_count_display(self, obj):
        count = obj.reply_count
        return format_html('<span style="color: #28a745;">💬 {}</span>', count)
    reply_count_display.short_description = 'Replies'
    
    def upvote_count_display(self, obj):
        count = obj.upvote_count
        return format_html('<span style="color: #dc3545;">👍 {}</span>', count)
    upvote_count_display.short_description = 'Upvotes'
    
    def is_flagged_badge(self, obj):
        if obj.is_flagged:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠️ Flagged</span>')
        return format_html('<span style="color: #6c757d;">—</span>')
    is_flagged_badge.short_description = 'Flagged'
    
    actions = ['mark_solved', 'pin_posts', 'unpin_posts', 'hide_posts', 'unhide_posts']
    
    def mark_solved(self, request, queryset):
        updated = queryset.update(is_solved=True, status='solved')
        self.message_user(request, f'{updated} post(s) marked as solved')
    mark_solved.short_description = "Mark as solved"
    
    def pin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=True, status='pinned')
        self.message_user(request, f'{updated} post(s) pinned')
    pin_posts.short_description = "Pin selected posts"
    
    def unpin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} post(s) unpinned')
    unpin_posts.short_description = "Unpin selected posts"
    
    def hide_posts(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f'{updated} post(s) hidden')
    hide_posts.short_description = "Hide selected posts"
    
    def unhide_posts(self, request, queryset):
        updated = queryset.update(is_hidden=False)
        self.message_user(request, f'{updated} post(s) unhidden')
    unhide_posts.short_description = "Unhide selected posts"


@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = [
        'post_title', 'author_name', 'upvote_count_display',
        'is_accepted_badge', 'is_hidden_badge', 'created_at'
    ]
    list_filter = ['is_accepted', 'is_hidden', 'created_at']
    search_fields = ['post__title', 'author__username', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def post_title(self, obj):
        return obj.post.title[:50]
    post_title.short_description = 'Post'
    
    def author_name(self, obj):
        return obj.author.display_name
    author_name.short_description = 'Author'
    
    def upvote_count_display(self, obj):
        count = obj.upvote_count
        return format_html('<span style="color: #dc3545;">👍 {}</span>', count)
    upvote_count_display.short_description = 'Upvotes'
    
    def is_accepted_badge(self, obj):
        if obj.is_accepted:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Accepted</span>')
        return format_html('<span style="color: #6c757d;">—</span>')
    is_accepted_badge.short_description = 'Accepted'
    
    def is_hidden_badge(self, obj):
        if obj.is_hidden:
            return format_html('<span style="color: #dc3545;">Hidden</span>')
        return format_html('<span style="color: #28a745;">Visible</span>')
    is_hidden_badge.short_description = 'Status'
    
    actions = ['accept_replies', 'hide_replies', 'unhide_replies']
    
    def accept_replies(self, request, queryset):
        for reply in queryset:
            reply.is_accepted = True
            reply.save()
            # Mark post as solved if this reply is accepted
            if reply.post:
                reply.post.mark_solved(reply)
        self.message_user(request, f'{queryset.count()} reply(ies) accepted')
    accept_replies.short_description = "Accept as solution"
    
    def hide_replies(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f'{updated} reply(ies) hidden')
    hide_replies.short_description = "Hide selected replies"
    
    def unhide_replies(self, request, queryset):
        updated = queryset.update(is_hidden=False)
        self.message_user(request, f'{updated} reply(ies) unhidden')
    unhide_replies.short_description = "Unhide selected replies"


@admin.register(ForumNotification)
class ForumNotificationAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'notification_type', 'post_title', 'is_read_badge', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'post__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def post_title(self, obj):
        if obj.post:
            return obj.post.title[:50]
        return '—'
    post_title.short_description = 'Post'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #28a745;">✓ Read</span>')
        return format_html('<span style="color: #dc3545;">✗ Unread</span>')
    is_read_badge.short_description = 'Status'
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read')
    mark_as_read.short_description = "Mark as read"