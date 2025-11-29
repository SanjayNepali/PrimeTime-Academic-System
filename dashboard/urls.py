# File: Desktop/Prime/dashboard/urls.py

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    
    # Add these missing routes for new features
    path('switch-role/', views.switch_role, name='switch_role'),
    path('profile/', views.user_profile, name='user_profile'),

    path('api/system-health/', views.system_health_api, name='system_health_api'),
]