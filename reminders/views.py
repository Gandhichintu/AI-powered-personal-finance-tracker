from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Reminder

@login_required
def notifications(request):
    """
    Show all notifications for the user
    """
    # Get all reminders for the user
    reminders = Reminder.objects.filter(user=request.user).order_by('-remind_on')
    
    # Separate by status
    pending_reminders = reminders.filter(status='pending')
    sent_reminders = reminders.filter(status='sent')
    
    # Mark as notified when viewed
    for reminder in pending_reminders:
        if not reminder.in_app_notified:
            reminder.mark_as_notified()
    
    return render(request, 'reminders/notifications.html', {
        'pending_reminders': pending_reminders,
        'sent_reminders': sent_reminders,
        'today': timezone.now().date(),
    })

@login_required
def mark_as_read(request, reminder_id):
    """
    Mark a reminder as read/notified
    """
    reminder = Reminder.objects.filter(id=reminder_id, user=request.user).first()
    
    if reminder:
        reminder.mark_as_notified()
        messages.success(request, 'Reminder marked as read')
    
    return redirect('reminders:notifications')

@login_required
def clear_notification(request, reminder_id):
    """
    Clear/delete a notification
    """
    reminder = Reminder.objects.filter(id=reminder_id, user=request.user).first()
    
    if reminder:
        reminder.delete()
        messages.success(request, 'Notification cleared')
    
    return redirect('reminders:notifications')

@login_required
def clear_all_notifications(request):
    """
    Clear all notifications for the user
    """
    Reminder.objects.filter(user=request.user, in_app_notified=True).delete()
    messages.success(request, 'All read notifications cleared')
    
    return redirect('reminders:notifications')