# File: projects/urls.py - COMPLETE FIXED VERSION

from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # ========== GROUP MEETING ROUTES ==========
    path('group/<int:group_id>/schedule-meeting/', views.schedule_group_meeting, name='schedule_group_meeting'),
    path('meeting/<int:meeting_id>/record-minutes/', views.record_group_meeting_minutes, name='record_group_meeting_minutes'),
    path('meeting/<int:meeting_id>/approve-logsheets/', views.approve_group_logsheets, name='approve_group_logsheets'),
    path('logsheet/<int:logsheet_id>/submit/', views.student_submit_logsheet, name='student_submit_logsheet'),
    
    # ========== STUDENT ROUTES ==========
    path('my-project/', views.my_project, name='my_project'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/submit/', views.project_submit, name='project_submit'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/analytics/', views.project_analytics, name='project_analytics'),  # FIXED: Added this line
    path('<int:pk>/wellness/', views.project_wellness, name='project_wellness'),
    path('<int:pk>/stress-analysis/', views.stress_analysis, name='stress_analysis'),
    path('<int:pk>/team/', views.project_team, name='project_team'),
    path('<int:pk>/collaboration/', views.project_collaboration, name='project_collaboration'),
    path('<int:pk>/recommendations/', views.project_recommendations, name='project_recommendations'),
    
    # ========== SUPERVISOR ROUTES ==========
    path('supervisor-projects/', views.supervisor_projects, name='supervisor_projects'),
    path('supervisor/<int:pk>/', views.supervisor_project_detail, name='supervisor_project_detail'),
    path('logsheet/<int:pk>/approve/', views.approve_log_sheet, name='approve_log_sheet'),
    path('supervisor/<int:pk>/add-progress-note/', views.add_progress_note, name='add_progress_note'),
    
    # ========== ADMIN ROUTES ==========
    path('all-projects/', views.all_projects, name='all_projects'),
    path('<int:pk>/review/', views.project_review, name='project_review'),
    path('<int:pk>/assign-supervisor/', views.assign_supervisor_page, name='assign_supervisor_page'),
    
    # ========== GENERAL ROUTES ==========
    path('', views.project_list, name='project_list'),
]