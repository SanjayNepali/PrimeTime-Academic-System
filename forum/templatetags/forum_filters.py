# File: forum/templatetags/forum_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def has_upvoted(reply, user):
    """Check if user has upvoted this reply"""
    return reply.upvotes.filter(pk=user.pk).exists()