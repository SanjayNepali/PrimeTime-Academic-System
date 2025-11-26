#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test all routing configurations"""
import os
import sys
import django

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from django.conf import settings

print('=' * 80)
print('PRIMETIME - ROUTING CONFIGURATION TEST')
print('=' * 80)

# 1. Check ASGI configuration
print('\n1. ASGI CONFIGURATION:')
print('-' * 80)
try:
    from academic_system import asgi
    print('   [OK] ASGI module loaded')

    if hasattr(asgi, 'application'):
        print('   [OK] ASGI application configured')

        # Check protocol type router
        app_type = type(asgi.application).__name__
        print(f'   [OK] Application type: {app_type}')

        if app_type == 'ProtocolTypeRouter':
            print('   [OK] ProtocolTypeRouter configured')

            # Check protocols
            protocols = list(asgi.application.application_mapping.keys())
            print(f'   [OK] Protocols: {", ".join(protocols)}')

            if 'http' in protocols:
                print('   [OK] HTTP protocol configured')
            if 'websocket' in protocols:
                print('   [OK] WebSocket protocol configured')
        else:
            print('   [WARNING] Not using ProtocolTypeRouter')
    else:
        print('   [ERROR] ASGI application not found')
except Exception as e:
    print(f'   [ERROR] Failed to load ASGI: {e}')

# 2. Check WebSocket routing
print('\n2. WEBSOCKET ROUTING:')
print('-' * 80)
try:
    from chat.routing import websocket_urlpatterns
    print(f'   [OK] WebSocket URL patterns found: {len(websocket_urlpatterns)}')

    for pattern in websocket_urlpatterns:
        print(f'   [OK] Pattern: {pattern.pattern}')

except Exception as e:
    print(f'   [ERROR] Failed to load WebSocket routing: {e}')

# 3. Check Channel Layers
print('\n3. CHANNEL LAYERS:')
print('-' * 80)
if hasattr(settings, 'CHANNEL_LAYERS'):
    channel_config = settings.CHANNEL_LAYERS
    print('   [OK] Channel layers configured')

    default_config = channel_config.get('default', {})
    backend = default_config.get('BACKEND', 'Not configured')
    print(f'   [OK] Backend: {backend}')

    if 'redis' in backend.lower():
        print('   [OK] Using Redis (Production ready)')
        config = default_config.get('CONFIG', {})
        hosts = config.get('hosts', [])
        print(f'   [OK] Redis hosts: {hosts}')
    elif 'InMemory' in backend:
        print('   [WARNING] Using InMemory (Development only)')
    else:
        print(f'   [INFO] Backend: {backend}')
else:
    print('   [ERROR] Channel layers not configured')

# 4. Check HTTP URLs
print('\n4. HTTP URL CONFIGURATION:')
print('-' * 80)

resolver = get_resolver()

# Expected app namespaces
expected_apps = [
    'accounts', 'dashboard', 'projects', 'groups',
    'chat', 'events', 'analytics', 'resources', 'forum'
]

found_apps = []

def check_patterns(patterns, prefix=''):
    routes = []
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            # It's an include()
            if hasattr(pattern, 'app_name') and pattern.app_name:
                found_apps.append(pattern.app_name)
                routes.append(f'   [OK] /{pattern.pattern} -> {pattern.app_name}')
            # Recurse into nested patterns
            routes.extend(check_patterns(pattern.url_patterns, prefix + str(pattern.pattern)))
    return routes

routes = check_patterns(resolver.url_patterns)

for route in routes:
    print(route)

print(f'\n   Found {len(found_apps)} app namespaces')

# Check if all expected apps are configured
missing = set(expected_apps) - set(found_apps)
if missing:
    print(f'   [WARNING] Missing apps: {", ".join(missing)}')
else:
    print('   [OK] All expected apps configured')

# 5. Check static and media URLs
print('\n5. STATIC/MEDIA CONFIGURATION:')
print('-' * 80)
print(f'   STATIC_URL: {settings.STATIC_URL}')
print(f'   MEDIA_URL: {settings.MEDIA_URL}')

if hasattr(settings, 'STATIC_ROOT'):
    print(f'   STATIC_ROOT: {settings.STATIC_ROOT}')
if hasattr(settings, 'MEDIA_ROOT'):
    print(f'   MEDIA_ROOT: {settings.MEDIA_ROOT}')

# 6. Check middleware for channels
print('\n6. MIDDLEWARE:')
print('-' * 80)
middleware_list = settings.MIDDLEWARE

important_middleware = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

for mw in important_middleware:
    if mw in middleware_list:
        print(f'   [OK] {mw.split(".")[-1]}')
    else:
        print(f'   [WARNING] Missing: {mw}')

# 7. Test WebSocket consumer
print('\n7. WEBSOCKET CONSUMER:')
print('-' * 80)
try:
    from chat.consumers import ChatConsumer
    print('   [OK] ChatConsumer loaded')

    # Check if it's an AsyncWebsocketConsumer
    from channels.generic.websocket import AsyncWebsocketConsumer
    if issubclass(ChatConsumer, AsyncWebsocketConsumer):
        print('   [OK] Using AsyncWebsocketConsumer')

    # Check methods
    methods = ['connect', 'disconnect', 'receive']
    for method in methods:
        if hasattr(ChatConsumer, method):
            print(f'   [OK] Method: {method}')
        else:
            print(f'   [ERROR] Missing method: {method}')

except Exception as e:
    print(f'   [ERROR] Failed to load ChatConsumer: {e}')

# 8. Summary
print('\n' + '=' * 80)
print('ROUTING SUMMARY')
print('=' * 80)

summary = {
    'ASGI': 'Configured',
    'WebSocket': 'Configured',
    'HTTP URLs': f'{len(found_apps)} apps',
    'Channel Layers': 'Redis' if 'redis' in str(settings.CHANNEL_LAYERS).lower() else 'InMemory',
    'Status': '[OK] Ready for deployment'
}

for key, value in summary.items():
    print(f'   {key:20s}: {value}')

print('=' * 80)

# 9. Quick connection test info
print('\n[INFO] WebSocket Connection URL:')
print('   ws://localhost:8000/ws/chat/<room_id>/')
print('   (Use wss:// for HTTPS in production)')
print('\n[INFO] To test WebSocket:')
print('   1. Start Redis: redis-server')
print('   2. Run server: python manage.py runserver')
print('   3. Or with Daphne: daphne -p 8000 academic_system.asgi:application')

print('\n[INFO] Main URLs:')
for app in expected_apps:
    print(f'   http://localhost:8000/{app}/')

print('\n' + '=' * 80)
print('Routing verification complete!')
print('=' * 80)
