# File: chat/templatetags/chat_extras.py
from django import template

register = template.Library()

@register.filter
def extract_role(choice_label):
    """Extract role from choice label format: 'Name (Role)'"""
    if '(' in choice_label and ')' in choice_label:
        role_start = choice_label.find('(') + 1
        role_end = choice_label.find(')')
        return choice_label[role_start:role_end]
    return 'User'

@register.filter
def extract_name(choice_label):
    """Extract name from choice label format: 'Name (Role)'"""
    if '(' in choice_label:
        return choice_label.split('(')[0].strip()
    return choice_label

@register.filter
def role_badge_class(role):
    """Get CSS class for role badge"""
    role = role.lower()
    if role == 'admin':
        return 'role-admin'
    elif role == 'supervisor':
        return 'role-supervisor'
    elif role == 'student':
        return 'role-student'
    return 'role-user'