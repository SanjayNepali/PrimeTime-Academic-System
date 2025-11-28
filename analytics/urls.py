# File: analytics/urls.py

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Student analytics
    path('my-analytics/', views.my_analytics, name='my_analytics'),
    path('run-analysis/', views.run_stress_analysis, name='run_stress_analysis'),
    path('my-feedback/', views.student_view_feedback, name='student_view_feedback'),

    # Supervisor analytics
    path('supervisor/', views.supervisor_analytics, name='supervisor_analytics'),
    path('student/<int:student_id>/stress/', views.student_stress_detail, name='student_stress_detail'),

    # Supervisor student monitoring and feedback - REMOVED DUPLICATE
    path('supervisor/student/<int:student_id>/', views.supervisor_view_student_profile, name='supervisor_view_student'),
    path('supervisor/student/<int:student_id>/add-feedback/', views.supervisor_add_feedback, name='supervisor_add_feedback'),

    # Admin analytics and log sheets
    path('admin/', views.admin_analytics, name='admin_analytics'),
    path('admin/all-logsheets/', views.admin_view_all_logsheets, name='admin_view_all_logsheets'),
    
    # Debug URL (optional)
    path('debug-stress/', views.debug_stress_calculation, name='debug_stress'),
]