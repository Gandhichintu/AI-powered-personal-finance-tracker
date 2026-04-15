# expenses/templatetags/dict_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_attribute(obj, attr):
    """Get an attribute from an object"""
    if obj is None:
        return None
    return getattr(obj, attr, None)