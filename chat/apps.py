# ============================================
# File: chat/apps.py (MODIFY THIS FILE)
# PURPOSE: Register signals
# ============================================

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Chat & Messaging'

    def ready(self):
        """Import signals when app is ready"""
        import chat.signals