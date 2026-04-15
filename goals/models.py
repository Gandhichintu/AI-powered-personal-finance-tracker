from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        percentage = (self.saved_amount / self.target_amount) * 100
        return min(100, float(percentage))  # Cap at 100%
    
    def days_left(self):
        from django.utils.timezone import now
        delta = (self.deadline - now().date()).days
        return max(0, delta)  # Don't show negative days
    
    def status(self):
        if self.is_completed:
            return "Completed"
        if self.days_left() == 0:
            return "Due Today"
        if self.days_left() < 7:
            return "Due Soon"
        return "On Track"
    
    def save(self, *args, **kwargs):
        # Update completed_at when marked as completed
        if self.is_completed and not self.completed_at:
            from django.utils.timezone import now
            self.completed_at = now()
        elif not self.is_completed:
            self.completed_at = None
        
        # Ensure saved_amount doesn't exceed target_amount
        if self.saved_amount > self.target_amount:
            self.saved_amount = self.target_amount
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} (₹{self.saved_amount}/₹{self.target_amount})"