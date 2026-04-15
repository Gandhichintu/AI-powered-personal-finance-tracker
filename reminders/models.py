from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now
import uuid

User = get_user_model()

class Reminder(models.Model):
    """Model to store all types of reminders"""
    REMINDER_TYPES = [
        ('goal', 'Savings Goal'),
        ('recurring', 'Recurring Payment'),
        ('group_expense', 'Group Expense'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Content fields
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Dates
    due_date = models.DateField()  # When the actual event is due
    remind_on = models.DateField()  # When to send the reminder
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Foreign keys (optional, for linking to actual items)
    goal = models.ForeignKey('goals.SavingsGoal', on_delete=models.SET_NULL, null=True, blank=True)
    recurring_payment = models.ForeignKey('recurring.RecurringPayment', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Tracking
    email_sent = models.BooleanField(default=False)
    in_app_notified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['remind_on', 'created_at']
        indexes = [
            models.Index(fields=['user', 'remind_on', 'status']),
            models.Index(fields=['remind_on', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def is_overdue(self):
        """Check if the due date has passed"""
        return self.due_date < now().date()
    
    def days_until_due(self):
        """Days until due date (negative if overdue)"""
        return (self.due_date - now().date()).days
    
    def mark_as_sent(self):
        """Mark reminder as sent"""
        self.status = 'sent'
        self.sent_at = now()
        self.email_sent = True
        self.save()
    
    def mark_as_notified(self):
        """Mark as notified in app"""
        self.in_app_notified = True
        self.save()


class ReminderRule(models.Model):
    """Rules for when to create reminders"""
    REMINDER_TYPES = [
        ('goal', 'Savings Goal'),
        ('recurring', 'Recurring Payment'),
    ]
    
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    days_before = models.IntegerField(help_text="Days before due date (0 = on due date, -1 = after due date)")
    enabled = models.BooleanField(default=True)
    
    # Template fields
    subject_template = models.CharField(max_length=200)
    message_template = models.TextField()
    
    class Meta:
        unique_together = ['reminder_type', 'days_before']
    
    def __str__(self):
        prefix = "Overdue" if self.days_before == -1 else f"{self.days_before} days before"
        return f"{self.get_reminder_type_display()} - {prefix}"
    
    def get_subject(self, **context):
        """Format subject with context"""
        return self.subject_template.format(**context)
    
    def get_message(self, **context):
        """Format message with context"""
        return self.message_template.format(**context)


class EmailLog(models.Model):
    """Log all emails sent for auditing"""
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='email_logs')
    sent_to = models.EmailField()
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('failed', 'Failed')])
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Email to {self.sent_to} - {self.status}"