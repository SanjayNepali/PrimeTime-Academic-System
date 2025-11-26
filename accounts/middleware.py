# File: Desktop/Prime/accounts/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class ForcePasswordChangeMiddleware:
    """Force users to change their initial password on first login"""
    
    EXEMPT_URLS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/static/',
        '/media/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._message_shown = set()  # Track which users have seen the message
    
    def __call__(self, request):
        # Skip for exempt URLs
        for url in self.EXEMPT_URLS:
            if request.path.startswith(url):
                return self.get_response(request)
        
        # Skip for anonymous users
        if not request.user.is_authenticated:
            if not request.path.startswith('/accounts/'):
                return redirect(f"{reverse('accounts:login')}?next={request.path}")
            return self.get_response(request)
        
        # Superusers bypass password change requirement
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Allowed URLs for authenticated users who must change password
        allowed_urls = [
            reverse('accounts:change_password'),
            reverse('accounts:logout'),
        ]
        
        # Check if user must change password
        if hasattr(request.user, 'must_change_password') and request.user.must_change_password:
            if request.path not in allowed_urls:
                # Only show message once per session
                session_key = f'pwd_msg_{request.user.id}'
                if not request.session.get(session_key, False):
                    messages.warning(request, 'You must change your initial password before continuing.')
                    request.session[session_key] = True
                return redirect('accounts:change_password')
        
        return self.get_response(request)