# File: events/urls.py

from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Event management
    path('', views.event_list, name='event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_update, name='event_update'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:pk>/cancel/', views.event_cancel, name='event_cancel'),

    # RSVP
    path('<int:pk>/rsvp/<str:status>/', views.rsvp_event, name='rsvp_event'),

    # My events
    path('my-events/', views.my_events, name='my_events'),

    # Calendar views
    path('calendar/', views.event_calendar_view, name='calendar_view'),
    path('calendars/', views.calendar_list, name='calendar_list'),
    path('calendars/create/', views.calendar_create, name='calendar_create'),
    path('calendars/<int:pk>/', views.calendar_detail, name='calendar_detail'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('api/system-notifications/', views.get_system_notifications, name='get_system_notifications'),
    # AJAX endpoints
    path('api/unread-notifications/', views.get_unread_notifications, name='api_unread_notifications'),

    # Event submissions (students)
    path('submit/<int:event_id>/', views.submit_to_event, name='submit_to_event'),
    path('my-submissions/', views.my_submissions, name='my_submissions'),

    # Deadline event creation (admin)
    path('create-deadline/', views.create_deadline_event, name='create_deadline_event'),

    # Supervisor submission review
    path('submissions/review/', views.supervisor_review_submissions, name='supervisor_review_submissions'),
    path('submissions/review/<int:submission_id>/', views.supervisor_review_submission_detail, name='supervisor_review_submission_detail'),

    # Admin submission review
    path('submissions/admin-review/', views.admin_review_submissions, name='admin_review_submissions'),
    path('submissions/admin-review/<int:submission_id>/', views.admin_review_submission_detail, name='admin_review_submission_detail'),
]
