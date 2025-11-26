# ========================================
# File: Desktop/Prime/academic_system/urls.py (UPDATED)
# ========================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('projects/', include('projects.urls')),
    path('groups/', include('groups.urls')),
    path('events/', include('events.urls')),
    path('analytics/', include('analytics.urls')),
    path('resources/', include('resources.urls')),  # NEW
    path('forum/', include('forum.urls')),           # NEW
    path('chat/', include('chat.urls')),             # NEW
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)