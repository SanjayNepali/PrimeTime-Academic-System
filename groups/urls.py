# File: groups/urls.py

from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Group management
    path('', views.group_list, name='group_list'),
    path('create/', views.group_create, name='group_create'),
    path('<int:pk>/', views.group_detail, name='group_detail'),
    path('<int:pk>/edit/', views.group_update, name='group_update'),
    path('<int:pk>/delete/', views.group_delete, name='group_delete'),

    # Student management
    path('<int:pk>/add-student/', views.add_student, name='add_student'),
    path('<int:pk>/bulk-add-students/', views.bulk_add_students, name='bulk_add_students'),
    path('<int:pk>/remove-student/<int:student_id>/', views.remove_student, name='remove_student'),

    # Student views
    path('my-group/', views.my_group, name='my_group'),

    # Activities
    path('<int:pk>/activities/', views.group_activities, name='group_activities'),

    # AJAX endpoints
    path('api/available-students/', views.get_available_students, name='api_available_students'),
]
