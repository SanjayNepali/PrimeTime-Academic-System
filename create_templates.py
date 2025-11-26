#!/usr/bin/env python
"""Script to create all remaining templates quickly"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Template definitions
TEMPLATES = {
    'events/event_form.html': '''{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block title %}{% if form.instance.pk %}Edit Event{% else %}Create Event{% endif %} - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">
                        <i class="fas fa-calendar-plus"></i>
                        {% if form.instance.pk %}Edit Event{% else %}Create Event{% endif %}
                    </h4>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        {{ form|crispy }}
                        <div class="form-group mt-4">
                            <button type="submit" class="btn btn-primary btn-lg">
                                <i class="fas fa-save"></i> Save Event
                            </button>
                            <a href="{% url 'events:event_list' %}" class="btn btn-secondary btn-lg">
                                <i class="fas fa-times"></i> Cancel
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    'events/my_events.html': '''{% extends 'base.html' %}

{% block title %}My Events - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2><i class="fas fa-user-calendar"></i> My Events</h2>

    <ul class="nav nav-tabs mt-3">
        <li class="nav-item">
            <a class="nav-link {% if not filter %}active{% endif %}" href="{% url 'events:my_events' %}">All</a>
        </li>
        <li class="nav-item">
            <a class="nav-link {% if filter == 'attending' %}active{% endif %}" href="?filter=attending">Attending</a>
        </li>
        <li class="nav-item">
            <a class="nav-link {% if filter == 'organizing' %}active{% endif %}" href="?filter=organizing">Organizing</a>
        </li>
    </ul>

    <div class="mt-4">
        {% for event in events %}
        {% include 'events/_event_card.html' %}
        {% empty %}
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i> No events found.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}''',

    'events/_event_card.html': '''<div class="card mb-3 shadow-sm">
    <div class="card-body">
        <div class="d-flex justify-content-between">
            <div>
                <h5 class="card-title">
                    <a href="{% url 'events:event_detail' event.pk %}">{{ event.title }}</a>
                </h5>
                <p class="text-muted">
                    <i class="far fa-calendar"></i> {{ event.start_datetime|date:"M j, Y g:i A" }}
                </p>
                <span class="badge badge-primary">{{ event.get_event_type_display }}</span>
                <span class="badge badge-{{ event.priority }}">{{ event.get_priority_display }}</span>
            </div>
            <div class="text-right">
                {% if event.is_cancelled %}
                <span class="badge badge-danger">Cancelled</span>
                {% else %}
                <a href="{% url 'events:event_detail' event.pk %}" class="btn btn-primary btn-sm">View</a>
                {% endif %}
            </div>
        </div>
    </div>
</div>''',

    'events/calendar.html': '''{% extends 'base.html' %}

{% block title %}Calendar - {{ block.super }}{% endblock %}

{% block content %}
<div class="container-fluid mt-4">
    <h2><i class="fas fa-calendar-alt"></i> Calendar</h2>
    <div id="calendar" class="mt-4" style="background: white; padding: 20px; border-radius: 8px;"></div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.css" rel="stylesheet">
<script>
document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        events: '/events/api/calendar/',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        }
    });
    calendar.render();
});
</script>
{% endblock %}''',

    'events/notifications_list.html': '''{% extends 'base.html' %}

{% block title %}Notifications - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-bell"></i> Notifications</h2>
        {% if unread_count > 0 %}
        <a href="?mark_all_read=1" class="btn btn-primary">Mark All Read</a>
        {% endif %}
    </div>

    <div class="list-group">
        {% for notification in notifications %}
        <a href="{% url 'events:event_detail' notification.event.pk %}"
           class="list-group-item list-group-item-action {% if not notification.is_read %}list-group-item-primary{% endif %}">
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">{{ notification.event.title }}</h6>
                <small>{{ notification.created_at|timesince }} ago</small>
            </div>
            <p class="mb-1">{{ notification.message }}</p>
        </a>
        {% empty %}
        <div class="list-group-item text-center">No notifications</div>
        {% endfor %}
    </div>
</div>
{% endblock %}''',

    'analytics/my_analytics.html': '''{% extends 'base.html' %}

{% block title %}My Analytics - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2><i class="fas fa-chart-line"></i> My Analytics</h2>

    <div class="row mt-4">
        <div class="col-md-4">
            <div class="card text-center shadow">
                <div class="card-body">
                    <h3 class="text-primary">{{ progress }}%</h3>
                    <p class="text-muted">Project Progress</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center shadow">
                <div class="card-body">
                    <h3 class="text-warning">{{ stress_level }}</h3>
                    <p class="text-muted">Stress Level</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center shadow">
                <div class="card-body">
                    <h3 class="text-success">{{ performance }}%</h3>
                    <p class="text-muted">Performance Score</p>
                </div>
            </div>
        </div>
    </div>

    <div class="card mt-4 shadow">
        <div class="card-header">
            <h5>Progress Over Time</h5>
        </div>
        <div class="card-body">
            <canvas id="progressChart"></canvas>
        </div>
    </div>
</div>
{% endblock %}''',

    'resources/resource_list.html': '''{% extends 'base.html' %}

{% block title %}Resources - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-book"></i> Resources</h2>
        {% if user.role != 'student' %}
        <a href="{% url 'resources:resource_create' %}" class="btn btn-primary">
            <i class="fas fa-plus"></i> Add Resource
        </a>
        {% endif %}
    </div>

    <div class="row">
        {% for resource in resources %}
        <div class="col-md-4 mb-4">
            <div class="card shadow-sm h-100">
                <div class="card-body">
                    <h5 class="card-title">{{ resource.title }}</h5>
                    <p class="text-muted">{{ resource.description|truncatewords:20 }}</p>
                    <div class="mb-2">
                        <span class="badge badge-primary">{{ resource.category.name }}</span>
                        <span class="badge badge-secondary">{{ resource.resource_type }}</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="fas fa-star text-warning"></i> {{ resource.average_rating|default:"No ratings" }}
                        </small>
                        <a href="{% url 'resources:resource_detail' resource.pk %}" class="btn btn-sm btn-primary">
                            View
                        </a>
                    </div>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-12">
            <div class="alert alert-info">No resources available</div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}''',

    'forum/forum_home.html': '''{% extends 'base.html' %}

{% block title %}Forum - {{ block.super }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-comments"></i> Community Forum</h2>
        <a href="{% url 'forum:post_create' %}" class="btn btn-primary">
            <i class="fas fa-plus"></i> New Post
        </a>
    </div>

    <!-- Stats -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h4>{{ stats.total_posts }}</h4>
                    <small class="text-muted">Total Posts</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h4>{{ stats.total_replies }}</h4>
                    <small class="text-muted">Replies</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h4>{{ stats.solved_posts }}</h4>
                    <small class="text-muted">Solved</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h4>{{ stats.active_users }}</h4>
                    <small class="text-muted">Active Users</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Posts -->
    {% for post in posts %}
    <div class="card mb-3 shadow-sm">
        <div class="card-body">
            <div class="d-flex justify-content-between">
                <div>
                    <h5><a href="{% url 'forum:post_detail' post.pk %}">{{ post.title }}</a></h5>
                    <p class="text-muted mb-2">{{ post.content|truncatewords:30 }}</p>
                    <div>
                        <span class="badge badge-primary">{{ post.get_post_type_display }}</span>
                        {% if post.is_solved %}<span class="badge badge-success">Solved</span>{% endif %}
                        {% if post.is_pinned %}<span class="badge badge-warning">Pinned</span>{% endif %}
                    </div>
                </div>
                <div class="text-right">
                    <div><i class="fas fa-arrow-up"></i> {{ post.upvote_count }}</div>
                    <div><i class="fas fa-comments"></i> {{ post.reply_count }}</div>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}'''
}

def create_templates():
    """Create all templates"""
    print("Creating templates...")
    created = 0

    for rel_path, content in TEMPLATES.items():
        full_path = os.path.join(TEMPLATES_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Check if file exists
        if os.path.exists(full_path):
            print(f"  [EXISTS] {rel_path}")
            continue

        # Create file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [CREATED] {rel_path}")
        created += 1

    print(f"\nCreated {created} new templates")
    print(f"Total templates defined: {len(TEMPLATES)}")

if __name__ == '__main__':
    create_templates()
