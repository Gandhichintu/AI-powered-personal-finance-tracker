import logging
from django.utils import timezone
from datetime import timedelta, date
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Reminder, ReminderRule, EmailLog
from goals.models import SavingsGoal
from recurring.models import RecurringPayment

logger = logging.getLogger(__name__)


def send_due_reminders():
    """
    Cron job to send due reminders
    Runs daily at 8:00 AM
    """
    logger.info("Starting send_due_reminders cron job")
    
    today = timezone.now().date()
    reminders_sent = 0
    errors = 0
    
    # Get all pending reminders due today or earlier
    reminders = Reminder.objects.filter(
        status='pending',
        remind_on__lte=today,
        email_sent=False
    ).select_related('user')
    
    logger.info(f"Found {reminders.count()} reminders to send")
    
    for reminder in reminders:
        try:
            with transaction.atomic():
                # Send email
                success = send_reminder_email(reminder)
                
                if success:
                    # Mark as sent
                    reminder.mark_as_sent()
                    reminders_sent += 1
                    logger.info(f"Sent reminder: {reminder.id} to {reminder.user.email}")
                else:
                    errors += 1
                    logger.error(f"Failed to send reminder: {reminder.id}")
                    
        except Exception as e:
            errors += 1
            logger.error(f"Error sending reminder {reminder.id}: {str(e)}")
    
    logger.info(f"Completed send_due_reminders. Sent: {reminders_sent}, Errors: {errors}")
    return f"Sent {reminders_sent} reminders, {errors} errors"


def generate_future_reminders():
    """
    Cron job to generate future reminders
    Runs daily at 8:15 AM
    """
    logger.info("Starting generate_future_reminders cron job")
    
    goals_created = generate_goal_reminders()
    payments_created = generate_payment_reminders()
    
    total = goals_created + payments_created
    logger.info(f"Generated {total} reminders (Goals: {goals_created}, Payments: {payments_created})")
    
    return f"Generated {total} reminders"


def generate_goal_reminders():
    """Generate reminders for savings goals"""
    created_count = 0
    today = timezone.now().date()
    
    # Get all active goals with future deadlines
    goals = SavingsGoal.objects.filter(
        is_completed=False,
        deadline__gte=today
    ).select_related('user')
    
    # Get reminder rules for goals
    rules = ReminderRule.objects.filter(
        reminder_type='goal',
        enabled=True
    )
    
    for goal in goals:
        for rule in rules:
            if should_create_goal_reminder(goal, rule):
                reminder = create_goal_reminder(goal, rule)
                if reminder:
                    created_count += 1
    
    return created_count


def generate_payment_reminders():
    """Generate reminders for recurring payments"""
    created_count = 0
    today = timezone.now().date()
    
    # Get all active payments with future due dates
    payments = RecurringPayment.objects.filter(
        is_active=True,
        next_payment_date__isnull=False
    ).select_related('user')
    
    # Get reminder rules for payments
    rules = ReminderRule.objects.filter(
        reminder_type='recurring',
        enabled=True
    )
    
    for payment in payments:
        for rule in rules:
            if should_create_payment_reminder(payment, rule):
                reminder = create_payment_reminder(payment, rule)
                if reminder:
                    created_count += 1
    
    return created_count


def should_create_goal_reminder(goal, rule):
    """Check if we should create a reminder for this goal with this rule"""
    from datetime import timedelta
    
    if rule.days_before == -1:  # Overdue reminder
        # Only create if deadline has passed and goal not completed
        if goal.deadline < timezone.now().date() and not goal.is_completed:
            remind_on = goal.deadline + timedelta(days=1)
        else:
            return False
    else:
        # Calculate reminder date
        remind_on = goal.deadline - timedelta(days=rule.days_before)
    
    # Don't create reminders in the past
    if remind_on < timezone.now().date():
        return False
    
    # Check if reminder already exists
    existing = Reminder.objects.filter(
        user=goal.user,
        goal=goal,
        remind_on=remind_on,
        reminder_type='goal'
    ).exists()
    
    return not existing


def should_create_payment_reminder(payment, rule):
    """Check if we should create a reminder for this payment with this rule"""
    from datetime import timedelta
    
    if rule.days_before == -1:  # Overdue reminder
        # Only create if payment date has passed
        if payment.next_payment_date < timezone.now().date():
            remind_on = payment.next_payment_date + timedelta(days=1)
        else:
            return False
    else:
        # Calculate reminder date
        remind_on = payment.next_payment_date - timedelta(days=rule.days_before)
    
    # Don't create reminders in the past
    if remind_on < timezone.now().date():
        return False
    
    # Check if reminder already exists
    existing = Reminder.objects.filter(
        user=payment.user,
        recurring_payment=payment,
        remind_on=remind_on,
        reminder_type='recurring'
    ).exists()
    
    return not existing


def create_goal_reminder(goal, rule):
    """Create a reminder for a savings goal"""
    from datetime import timedelta
    
    # Calculate dates
    if rule.days_before == -1:
        due_date = goal.deadline
        remind_on = goal.deadline + timedelta(days=1)
        title_prefix = "Overdue: "
    elif rule.days_before == 0:
        due_date = goal.deadline
        remind_on = goal.deadline
        title_prefix = "Due Today: "
    else:
        due_date = goal.deadline
        remind_on = goal.deadline - timedelta(days=rule.days_before)
        title_prefix = f"Due in {rule.days_before} days: "
    
    # Create context for template
    context = {
        'goal_name': goal.name,
        'target_amount': goal.target_amount,
        'saved_amount': goal.saved_amount,
        'progress': goal.progress_percentage(),
        'deadline': goal.deadline,
        'days_left': goal.days_left(),
    }
    
    # Create reminder
    reminder = Reminder.objects.create(
        user=goal.user,
        reminder_type='goal',
        title=f"{title_prefix}{goal.name}",
        message=rule.get_message(**context),
        due_date=due_date,
        remind_on=remind_on,
        goal=goal,
        status='pending'
    )
    
    return reminder


def create_payment_reminder(payment, rule):
    """Create a reminder for a recurring payment"""
    from datetime import timedelta
    
    # Calculate dates
    if rule.days_before == -1:
        due_date = payment.next_payment_date
        remind_on = payment.next_payment_date + timedelta(days=1)
        title_prefix = "Overdue: "
    elif rule.days_before == 0:
        due_date = payment.next_payment_date
        remind_on = payment.next_payment_date
        title_prefix = "Due Today: "
    else:
        due_date = payment.next_payment_date
        remind_on = payment.next_payment_date - timedelta(days=rule.days_before)
        title_prefix = f"Due in {rule.days_before} days: "
    
    # Create context for template
    context = {
        'payment_name': payment.name,
        'amount': payment.amount,
        'category': payment.get_category_display(),
        'frequency': payment.get_frequency_display(),
        'due_date': payment.next_payment_date,
        'days_until_due': payment.days_until_due(),
    }
    
    # Create reminder
    reminder = Reminder.objects.create(
        user=payment.user,
        reminder_type='recurring',
        title=f"{title_prefix}{payment.name}",
        message=rule.get_message(**context),
        due_date=due_date,
        remind_on=remind_on,
        recurring_payment=payment,
        status='pending'
    )
    
    return reminder


def send_reminder_email(reminder):
    """Send email for a reminder"""
    try:
        # Prepare email content
        subject = reminder.title
        message = reminder.message
        
        # Add HTML template
        html_message = render_to_string('reminders/email_template.html', {
            'reminder': reminder,
            'user': reminder.user,
        })
        
        # Send email
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reminder.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Log the email
        EmailLog.objects.create(
            reminder=reminder,
            sent_to=reminder.user.email,
            subject=subject,
            status='sent' if sent else 'failed'
        )
        
        return sent > 0
        
    except Exception as e:
        # Log the error
        EmailLog.objects.create(
            reminder=reminder,
            sent_to=reminder.user.email,
            subject=reminder.title,
            status='failed',
            error_message=str(e)
        )
        logger.error(f"Failed to send email for reminder {reminder.id}: {str(e)}")
        return False