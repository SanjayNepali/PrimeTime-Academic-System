# File: Desktop/Prime/chat/routing.py

from django.urls import re_path
from chat.consumers import ChatConsumer
from analytics.consumers import StressUpdateConsumer

websocket_urlpatterns = [
    # Existing chat WebSocket
    re_path(r'ws/chat/(?P<room_id>\d+)/$', ChatConsumer.as_asgi()),
    
    # NEW: Real-time stress updates WebSocket
    re_path(r'ws/stress/$', StressUpdateConsumer.as_asgi()),
]