# File: Desktop/Prime/accounts/urls.py

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('login-history/', views.login_history, name='login_history'),
    
    # User Management (Admin/Superadmin only)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/toggle/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
    
    # AJAX endpoints
    path('lookup-user/', views.lookup_user_by_id, name='lookup_user'),
]