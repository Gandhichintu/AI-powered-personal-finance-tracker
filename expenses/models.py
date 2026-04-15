# expenses/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from decimal import Decimal

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Shopping', 'Shopping'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Groceries', 'Groceries'),
        ('Fuel', 'Fuel'),
        ('Investment', 'Investment'),
        ('Other', 'Other'),
    ]
    
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    vendor = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Anomaly Detection Fields
    is_anomaly = models.BooleanField(default=False)
    anomaly_score = models.FloatField(null=True, blank=True)  # Z-score
    anomaly_reason = models.TextField(blank=True)
    reviewed = models.BooleanField(default=False)  # User has reviewed this anomaly
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['owner', 'date']),
            models.Index(fields=['owner', 'category', 'date']),
            models.Index(fields=['is_anomaly', 'reviewed']),
        ]

    def __str__(self):
        return f"{self.amount} - {self.vendor} - {self.date}"
    
    def mark_as_reviewed(self):
        """Mark anomaly as reviewed"""
        self.reviewed = True
        self.save()

class Receipt(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='receipts')
    image = models.ImageField(upload_to='receipts/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ocr_text = models.TextField(blank=True)
    parsed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parsed_date = models.DateField(null=True, blank=True)
    parsed_vendor = models.CharField(max_length=128, blank=True, default='Unknown Vendor')  # Add default value
    
    def __str__(self):
        return f"Receipt {self.pk} by {self.owner}"
    
class MonthlyAggregate(models.Model):
    """Store monthly aggregated expense data for predictions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_aggregates')
    month = models.DateField()  # First day of the month
    total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    categories = models.JSONField(default=dict)  # Store category breakdown
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'month']
        ordering = ['-month']
    
    def __str__(self):
        return f"{self.user.username} - {self.month.strftime('%B %Y')}: ₹{self.total_expense}"
    
class Income(models.Model):
    """Track user income"""
    INCOME_TYPES = [
        ('salary', 'Salary'),
        ('business', 'Business'),
        ('investment', 'Investment'),
        ('rental', 'Rental Income'),
        ('freelance', 'Freelance'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    source = models.CharField(max_length=100)
    income_type = models.CharField(max_length=20, choices=INCOME_TYPES)
    description = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.source}: ₹{self.amount} on {self.date}"


class Debt(models.Model):
    """Track user debts/liabilities"""
    DEBT_TYPES = [
        ('credit_card', 'Credit Card'),
        ('personal_loan', 'Personal Loan'),
        ('home_loan', 'Home Loan'),
        ('car_loan', 'Car Loan'),
        ('education_loan', 'Education Loan'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='debts')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = models.DateField()
    debt_type = models.CharField(max_length=20, choices=DEBT_TYPES)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}: ₹{self.amount}"


class Asset(models.Model):
    """Track user assets"""
    ASSET_TYPES = [
        ('cash', 'Cash'),
        ('savings', 'Savings Account'),
        ('investment', 'Investments'),
        ('property', 'Property'),
        ('vehicle', 'Vehicle'),
        ('retirement', 'Retirement Fund'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    purchase_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}: ₹{self.value}"


class EmergencyFund(models.Model):
    """Track emergency fund goals"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='emergency_fund')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_months = models.IntegerField(default=6)
    last_updated = models.DateTimeField(auto_now=True)
    
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0.0
        return float((self.current_amount / self.target_amount) * 100)
    
    def months_covered(self):
        """Returns float number of months covered"""
        from .analysis import SpendingAnalyzer
        analyzer = SpendingAnalyzer(self.user)
        monthly_avg = analyzer.get_monthly_data()['Total'].mean() if not analyzer.get_monthly_data().empty else 0
        if monthly_avg > 0:
            return float(self.current_amount / Decimal(str(monthly_avg)))
        return 0.0
    
    def __str__(self):
        return f"Emergency Fund: ₹{self.current_amount} / ₹{self.target_amount}"


class FinancialGoal(models.Model):
    """Track financial goals (different from savings goals)"""
    GOAL_TYPES = [
        ('emergency', 'Emergency Fund'),
        ('retirement', 'Retirement'),
        ('education', 'Education'),
        ('home', 'Home Purchase'),
        ('vacation', 'Vacation'),
        ('debt_free', 'Debt Free'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deadline = models.DateField()
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    def __str__(self):
        return f"{self.name}: {self.progress_percentage():.0f}%"