import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from goals.models import SavingsGoal
from recurring.models import RecurringPayment
from reminders.models import Reminder, ReminderRule
from reminders.cron import generate_goal_reminders, generate_payment_reminders

User = get_user_model()

def test_reminder_system():
    print("🧪 Testing Reminder System")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com', 'password': 'testpass123'}
    )
    
    if created:
        print("✅ Created test user")
    
    # Test 1: Create a savings goal
    print("\n1. Testing Savings Goal Reminders")
    goal = SavingsGoal.objects.create(
        user=user,
        name='Test Goal - Europe Trip',
        target_amount=50000,
        saved_amount=25000,
        deadline=date.today() + timedelta(days=10),  # 10 days from now
        is_completed=False
    )
    
    # Generate reminders
    goals_created = generate_goal_reminders()
    print(f"   Generated {goals_created} goal reminders")
    
    # Check created reminders
    goal_reminders = Reminder.objects.filter(user=user, reminder_type='goal')
    print(f"   Found {goal_reminders.count()} reminders for goal:")
    for r in goal_reminders:
        print(f"   - {r.title} (Due: {r.due_date}, Remind: {r.remind_on})")
    
    # Test 2: Create a recurring payment
    print("\n2. Testing Recurring Payment Reminders")
    payment = RecurringPayment.objects.create(
        user=user,
        name='Test Payment - Netflix',
        amount=499,
        category='subscription',
        frequency='monthly',
        next_payment_date=date.today() + timedelta(days=5),  # 5 days from now
        is_active=True
    )
    
    # Generate reminders
    payments_created = generate_payment_reminders()
    print(f"   Generated {payments_created} payment reminders")
    
    # Check created reminders
    payment_reminders = Reminder.objects.filter(user=user, reminder_type='recurring')
    print(f"   Found {payment_reminders.count()} reminders for payment:")
    for r in payment_reminders:
        print(f"   - {r.title} (Due: {r.due_date}, Remind: {r.remind_on})")
    
    # Test 3: Check rules
    print("\n3. Checking Reminder Rules")
    rules = ReminderRule.objects.all()
    print(f"   Found {rules.count()} reminder rules")
    for rule in rules:
        print(f"   - {rule}: {rule.days_before} days before")
    
    # Cleanup
    print("\n4. Cleaning up test data...")
    goal.delete()
    payment.delete()
    Reminder.objects.filter(user=user).delete()
    
    print("\n✅ All tests completed!")

if __name__ == '__main__':
    test_reminder_system()