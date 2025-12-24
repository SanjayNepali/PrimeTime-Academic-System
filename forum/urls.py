# File: forum/urls.py

from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # Main forum
    path('', views.forum_home, name='forum_home'),
    
    # Post CRUD
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/edit/', views.post_update, name='post_update'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    
    # Project-specific forum
    path('project/<int:project_id>/', views.project_forum, name='project_forum'),
    
    # Post interactions
    path('post/<int:pk>/upvote/', views.post_upvote, name='post_upvote'),
    path('post/<int:pk>/follow/', views.post_follow, name='post_follow'),
    path('post/<int:pk>/solved/', views.mark_solved, name='mark_solved'),
    path('post/<int:pk>/solved/<int:reply_id>/', views.mark_solved, name='mark_solved_reply'),  # FIX: Added reply_id
    
    # Reply interactions
    path('reply/<int:pk>/upvote/', views.reply_upvote, name='reply_upvote'),
    path('reply/<int:reply_id>/reply/', views.reply_to_reply, name='reply_to_reply'),  # NEW: Reply to reply
    
    # User posts
    path('my-posts/', views.my_posts, name='my_posts'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Moderation
    path('post/<int:pk>/flag/', views.flag_post, name='flag_post'),
    path('admin/flagged/', views.flagged_posts, name='flagged_posts'),
    
    # AJAX endpoints
    path('api/notifications/unread/', views.get_unread_notifications, name='api_unread_notifications'),
]