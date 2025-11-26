# File: Desktop/Prime/resources/urls.py

from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    # Resource CRUD
    path('', views.resource_list, name='resource_list'),
    path('create/', views.resource_create, name='resource_create'),
    path('<int:pk>/', views.resource_detail, name='resource_detail'),
    path('<int:pk>/edit/', views.resource_update, name='resource_update'),
    path('<int:pk>/delete/', views.resource_delete, name='resource_delete'),
    
    # Interaction
    path('<int:pk>/rate/', views.resource_rate, name='resource_rate'),
    path('<int:pk>/like/', views.resource_like, name='resource_like'),
    path('<int:pk>/download/', views.resource_download, name='resource_download'),
    
    # User resources
    path('my-resources/', views.my_resources, name='my_resources'),
    path('recommended/', views.recommended_resources, name='recommended_resources'),
    
    # Categories
    path('categories/', views.resource_categories, name='resource_categories'),
    path('category/<int:category_id>/', views.category_resources, name='category_resources'),
    
    # AJAX endpoints
    path('api/<int:pk>/mark-clicked/', views.mark_recommendation_clicked, name='mark_clicked'),
    
    # Admin
    path('admin/bulk-upload/', views.bulk_resource_upload, name='bulk_upload'),
    path('admin/pending/', views.pending_resources, name='pending_resources'),
    path('admin/<int:pk>/approve/', views.approve_resource, name='approve_resource'),
]