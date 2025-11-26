# File: events/notifications.py

from django.utils import timezone
from datetime import timedelta
from .models import Event, Notification, EventReminder


def send_event_reminders():
    """Send reminders for upcoming events"""
    now = timezone.now()
    events_needing_reminders = Event.objects.filter(
        is_active=True,
        is_cancelled=False,
        send_reminders=True,
        start_datetime__gt=now
    )

    reminders_sent = 0
    for event in events_needing_reminders:
        reminder_time = event.start_datetime - timedelta(hours=event.reminder_hours_before)
        if reminder_time <= now <= reminder_time + timedelta(hours=1):
            participants = event.participants.all()
            for user in participants:
                reminder, created = EventReminder.objects.get_or_create(event=event, user=user)
                if not reminder.is_sent:
                    Notification.objects.create(
                        recipient=user,
                        notification_type='event_reminder',
                        title=f"Reminder: {event.title}",
                        message=f"Your event '{event.title}' is scheduled for {event.start_datetime.strftime('%B %d, %Y at %I:%M %p')}",
                        event=event,
                        link_url=f"/events/{event.pk}/"
                    )
                    reminder.is_sent = True
                    reminder.reminder_sent_at = now
                    reminder.save()
                    reminders_sent += 1
    return reminders_sent


def notify_event_update(event, message):
    """Send notification to all participants when event is updated"""
    participants = event.participants.all()
    for user in participants:
        Notification.objects.create(
            recipient=user,
            notification_type='event_update',
            title=f"Event Updated: {event.title}",
            message=message,
            event=event,
            link_url=f"/events/{event.pk}/"
        )


def notify_event_cancelled(event):
    """Send notification when event is cancelled"""
    participants = event.participants.all()
    for user in participants:
        Notification.objects.create(
            recipient=user,
            notification_type='event_cancelled',
            title=f"Event Cancelled: {event.title}",
            message=f"The event '{event.title}' scheduled for {event.start_datetime.strftime('%B %d, %Y at %I:%M %p')} has been cancelled. Reason: {event.cancellation_reason or 'Not specified'}",
            event=event,
            link_url=f"/events/{event.pk}/"
        )
