from .models import Reminder

def pending_reminders_count(request):
    if request.user.is_authenticated:
        return {
            'pending_reminders_count': Reminder.objects.filter(
                user=request.user,
                status='pending',
                in_app_notified=False
            ).count()
        }
    return {'pending_reminders_count': 0}