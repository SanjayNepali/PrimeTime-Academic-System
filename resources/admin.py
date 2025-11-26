# File: Desktop/Prime/resources/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    ResourceCategory, ResourceTag, Resource, 
    ResourceRating, ResourceRecommendation, ResourceViewHistory
)


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color_display', 'order', 'resource_count']
    list_editable = ['order']
    search_fields = ['name', 'description']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 40px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(ResourceTag)
class ResourceTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'resource_count']
    search_fields = ['name']
    readonly_fields = ['created_at']
    
    def resource_count(self, obj):
        count = obj.resource_set.count()
        return format_html('<span class="badge">{}</span>', count)
    resource_count.short_description = 'Resources'


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'resource_type', 'category', 'difficulty_badge',
        'author_name', 'views_count', 'likes_count', 'rating_display',
        'approval_badge', 'featured_badge', 'created_at'
    ]
    list_filter = [
        'resource_type', 'difficulty', 'category', 
        'is_approved', 'is_featured', 'created_at'
    ]
    search_fields = ['title', 'description', 'programming_languages', 'author__username']
    readonly_fields = ['views', 'downloads', 'average_rating', 'rating_count', 'created_at', 'updated_at']
    filter_horizontal = ['tags', 'likes']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'resource_type', 'category', 'difficulty')
        }),
        ('Content', {
            'fields': ('url', 'file', 'thumbnail', 'estimated_duration')
        }),
        ('Classification', {
            'fields': ('tags', 'programming_languages')
        }),
        ('Author & Status', {
            'fields': ('author', 'is_approved', 'is_featured')
        }),
        ('Engagement Metrics', {
            'fields': ('views', 'likes', 'downloads', 'average_rating', 'rating_count', 'relevance_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def author_name(self, obj):
        return obj.author.display_name
    author_name.short_description = 'Author'
    author_name.admin_order_field = 'author__full_name'
    
    def views_count(self, obj):
        return format_html('<span style="color: #007bff;">👁 {}</span>', obj.views)
    views_count.short_description = 'Views'
    views_count.admin_order_field = 'views'
    
    def likes_count(self, obj):
        count = obj.like_count
        return format_html('<span style="color: #dc3545;">❤️ {}</span>', count)
    likes_count.short_description = 'Likes'
    
    def rating_display(self, obj):
        if obj.rating_count > 0:
            stars = '⭐' * int(obj.average_rating)
            return format_html(
                '{} <span style="color: #6c757d;">({:.1f}/5, {} ratings)</span>',
                stars, obj.average_rating, obj.rating_count
            )
        return format_html('<span style="color: #6c757d;">No ratings</span>')
    rating_display.short_description = 'Rating'
    
    def difficulty_badge(self, obj):
        colors = {
            'beginner': '#28a745',
            'intermediate': '#ffc107',
            'advanced': '#dc3545'
        }
        color = colors.get(obj.difficulty, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_difficulty_display()
        )
    difficulty_badge.short_description = 'Difficulty'
    
    def approval_badge(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: #28a745;">✓ Approved</span>')
        return format_html('<span style="color: #dc3545;">✗ Pending</span>')
    approval_badge.short_description = 'Status'
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color: #ffc107;">★ Featured</span>')
        return format_html('<span style="color: #6c757d;">—</span>')
    featured_badge.short_description = 'Featured'
    
    actions = ['approve_resources', 'feature_resources', 'unfeature_resources']
    
    def approve_resources(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} resource(s) approved')
    approve_resources.short_description = "Approve selected resources"
    
    def feature_resources(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} resource(s) marked as featured')
    feature_resources.short_description = "Mark as featured"
    
    def unfeature_resources(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} resource(s) unmarked as featured')
    unfeature_resources.short_description = "Remove featured status"


@admin.register(ResourceRating)
class ResourceRatingAdmin(admin.ModelAdmin):
    list_display = ['resource', 'user_name', 'rating_stars', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['resource__title', 'user__username', 'review']
    readonly_fields = ['created_at', 'updated_at']
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        return format_html('{} ({})', stars, obj.rating)
    rating_stars.short_description = 'Rating'


@admin.register(ResourceRecommendation)
class ResourceRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'resource', 'score_display', 'clicked', 'created_at']
    list_filter = ['clicked', 'algorithm_version', 'created_at']
    search_fields = ['user__username', 'resource__title', 'reason']
    readonly_fields = ['created_at', 'clicked_at']
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def score_display(self, obj):
        percentage = int(obj.score * 100)
        color = '#28a745' if obj.score > 0.7 else '#ffc107' if obj.score > 0.4 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, percentage
        )
    score_display.short_description = 'Score'
    score_display.admin_order_field = 'score'


@admin.register(ResourceViewHistory)
class ResourceViewHistoryAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'resource', 'viewed_at', 'time_display', 'completed']
    list_filter = ['completed', 'viewed_at']
    search_fields = ['user__username', 'resource__title']
    readonly_fields = ['viewed_at']
    
    def user_name(self, obj):
        return obj.user.display_name
    user_name.short_description = 'User'
    
    def time_display(self, obj):
        if obj.time_spent > 0:
            minutes = obj.time_spent // 60
            seconds = obj.time_spent % 60
            return format_html('{}m {}s', minutes, seconds)
        return '—'
    time_display.short_description = 'Time Spent'
    
    def has_add_permission(self, request):
        return False