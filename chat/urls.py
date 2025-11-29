# File: Desktop/Prime/chat/urls.py

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Main chat views
    path('', views.chat_home, name='chat_home'),
    path('room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('room/create/', views.create_room, name='create_room'),
    path('notifications/', views.chat_notifications, name='notifications'),
    
    # Direct messaging
    path('user/<int:user_id>/', views.user_chat, name='user_chat'),
    
    # Legacy routes (keep for compatibility)
    path('supervisor/<int:supervisor_id>/', views.supervisor_chat, name='supervisor_chat'),
    path('project/<int:project_id>/', views.project_forum, name='project_forum'),
    
    # Analytics
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # AJAX endpoints
    path('api/search-users/', views.search_users, name='api_search_users'),
    path('api/room/<int:room_id>/messages/', views.get_room_messages, name='api_room_messages'),
    path('api/unread-counts/', views.get_unread_counts, name='api_unread_counts'),
    path('api/student/<int:student_id>/stress/', views.analyze_student_stress, name='api_student_stress'),
]