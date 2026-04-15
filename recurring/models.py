from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class RecurringPayment(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    CATEGORY_CHOICES = [
        ('rent', 'Rent'),
        ('entertainment', 'Entertainment'),
        ('bills', 'Bills'),
        ('insurance', 'Insurance'),
        ('loan', 'Loan'),
        ('subscription', 'Subscription'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_payments')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    next_payment_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def days_until_due(self):
        from django.utils.timezone import now
        return (self.next_payment_date - now().date()).days

    def get_status_color(self):
        if not self.is_active:
            return 'gray'
        days = self.days_until_due()
        if days < 0:
            return 'red'
        elif days <= 3:
            return 'orange'
        elif days <= 7:
            return 'yellow'
        return 'green'

    def __str__(self):
        status = "Active" if self.is_active else "Paused"
        return f"{self.name} (₹{self.amount} - {self.frequency} - {status})"