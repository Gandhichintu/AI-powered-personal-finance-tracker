# recurring/utils.py

from django.utils.timezone import now
from .models import RecurringPayment

def get_due_payments(days=3):
    """
    Returns active recurring payments that are due within next `days`
    This will be used by Celery reminders (Phase 8)
    """
    today = now().date()
    upcoming = []

    payments = RecurringPayment.objects.filter(is_active=True)

    for p in payments:
        days_left = (p.next_payment_date - today).days
        if 0 <= days_left <= days:
            upcoming.append(p)

    return upcoming
