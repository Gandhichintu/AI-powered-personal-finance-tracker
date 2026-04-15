from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from goals.models import SavingsGoal
from recurring.models import RecurringPayment
from .models import Reminder, ReminderRule
from .cron import create_goal_reminder, create_payment_reminder, should_create_goal_reminder, should_create_payment_reminder

@receiver(post_save, sender=SavingsGoal)
def handle_goal_save(sender, instance, created, **kwargs):
    """
    Create reminders when a goal is saved
    """
    # Delete existing reminders for this goal
    Reminder.objects.filter(goal=instance).delete()
    
    # Only create reminders if goal is not completed and has future deadline
    if not instance.is_completed and instance.deadline >= timezone.now().date():
        # Get all enabled rules for goals
        rules = ReminderRule.objects.filter(
            reminder_type='goal',
            enabled=True
        )
        
        # Create reminders for each rule
        for rule in rules:
            if should_create_goal_reminder(instance, rule):
                create_goal_reminder(instance, rule)

@receiver(post_delete, sender=SavingsGoal)
def handle_goal_delete(sender, instance, **kwargs):
    """
    Delete reminders when a goal is deleted
    """
    Reminder.objects.filter(goal=instance).delete()

@receiver(post_save, sender=RecurringPayment)
def handle_payment_save(sender, instance, created, **kwargs):
    """
    Create reminders when a recurring payment is saved
    """
    # Delete existing reminders for this payment
    Reminder.objects.filter(recurring_payment=instance).delete()
    
    # Only create reminders if payment is active and has future due date
    if instance.is_active and instance.next_payment_date:
        # Get all enabled rules for payments
        rules = ReminderRule.objects.filter(
            reminder_type='recurring',
            enabled=True
        )
        
        # Create reminders for each rule
        for rule in rules:
            if should_create_payment_reminder(instance, rule):
                create_payment_reminder(instance, rule)

@receiver(post_delete, sender=RecurringPayment)
def handle_payment_delete(sender, instance, **kwargs):
    """
    Delete reminders when a payment is deleted
    """
    Reminder.objects.filter(recurring_payment=instance).delete()