# File: chat/templatetags/chat_extras.py - NEW FILE

from django import template

register = template.Library()


@register.filter
def extract_name(label):
    """Extract name from label like 'John Doe (Student)'"""
    if '(' in label:
        return label.split('(')[0].strip()
    return label


@register.filter
def extract_role(label):
    """Extract role from label like 'John Doe (Student)'"""
    if '(' in label and ')' in label:
        role = label.split('(')[1].split(')')[0].strip().lower()
        return role
    return 'student'


@register.filter
def role_badge_class(role):
    """Return CSS class for role badge"""
    role = role.lower()
    if role == 'admin':
        return 'role-admin'
    elif role == 'supervisor':
        return 'role-supervisor'
    else:
        return 'role-student'