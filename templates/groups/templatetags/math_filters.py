# groups/templatetags/math_filters.py
from django import template
import math

register = template.Library()

@register.filter
def abs_filter(value):
    """Absolute value filter"""
    try:
        return abs(value)
    except (TypeError, ValueError):
        try:
            return abs(float(value))
        except (TypeError, ValueError):
            return value

@register.filter(name='abs')  # Register as 'abs' for easier use
def absolute(value):
    """Another name for absolute value"""
    try:
        return abs(value)
    except (TypeError, ValueError):
        try:
            return abs(float(value))
        except (TypeError, ValueError):
            return value