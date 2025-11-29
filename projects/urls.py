# File: projects/urls.py - COMPLETE WITH ALL ROUTES

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
    
    # Analytics and recommendations routes
    path('<int:pk>/analytics/', views.project_analytics, name='project_analytics'),
    path('<int:pk>/recommendations/', views.project_recommendations, name='project_recommendations'),
    
    # Deliverable routes
    path('<int:pk>/deliverable/submit/', views.deliverable_submit, name='deliverable_submit'),
    
    # NEW: Wellness/Stress routes
    path('<int:pk>/wellness/', views.project_wellness, name='project_wellness'),
    path('<int:pk>/stress-analysis/', views.stress_analysis, name='stress_analysis'),
    
    # NEW: Team/Collaboration routes  
    path('<int:pk>/team/', views.project_team, name='project_team'),
    path('<int:pk>/collaboration/', views.project_collaboration, name='project_collaboration'),
    
    # Project list (role-based)
    path('', views.project_list, name='project_list'),
    
    # Admin routes
    path('all-projects/', views.all_projects, name='all_projects'),
    path('<int:pk>/review/', views.project_review, name='project_review'),
    path('<int:pk>/assign-supervisor/', views.project_assign_supervisor, name='project_assign_supervisor'),
    
    # Supervisor routes
    path('supervisor-projects/', views.supervisor_projects, name='supervisor_projects'),
]