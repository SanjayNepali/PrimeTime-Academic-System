# File: Desktop/Prime/projects/urls.py

from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Student routes
    path('my-project/', views.my_project, name='my_project'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/submit/', views.project_submit, name='project_submit'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    
    # Project list (role-based)
    path('', views.project_list, name='project_list'),
    
    # Superadmin/Admin routes
    path('all-projects/', views.all_projects, name='all_projects'),
    path('<int:pk>/review/', views.project_review, name='project_review'),
    
    # Add this missing route
    path('<int:pk>/assign-supervisor/', views.project_assign_supervisor, name='project_assign_supervisor'),
    
    # Supervisor routes
    path('supervisor-projects/', views.supervisor_projects, name='supervisor_projects'),
]