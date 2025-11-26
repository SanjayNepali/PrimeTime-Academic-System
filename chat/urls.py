# ========================================
# File: Desktop/Prime/chat/urls.py
# ========================================

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('room/create/', views.create_room, name='create_room'),
    path('notifications/', views.chat_notifications, name='notifications'),
    
    # AJAX
    path('api/room/<int:room_id>/messages/', views.get_room_messages, name='api_get_messages'),
]
