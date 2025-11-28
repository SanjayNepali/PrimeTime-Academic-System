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
    path('users/bulk-import/', views.bulk_user_import, name='bulk_user_import'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/toggle/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/reset-password/', views.user_reset_password_confirm, name='user_reset_password'),
    path('users/<int:pk>/reset-password/success/', views.password_reset_success, name='password_reset_success'),
    path('users/<int:pk>/disable/', views.user_disable_confirm, name='user_disable_confirm'),
    path('users/<int:pk>/enable/', views.user_enable_confirm, name='user_enable_confirm'),
    path('users/<int:pk>/delete/', views.user_confirm_delete, name='user_confirm_delete'),
    
    # AJAX endpoints
    path('lookup-user/', views.lookup_user_by_id, name='lookup_user'),
]