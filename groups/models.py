from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Group(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    invite_code = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class GroupExpense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - ₹{self.amount}"


class GroupExpenseShare(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    share_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.user} owes ₹{self.share_amount}"
