from django.core.management.base import BaseCommand
from reminders.models import ReminderRule

class Command(BaseCommand):
    help = 'Setup default reminder rules'
    
    def handle(self, *args, **kwargs):
        # Default rules for savings goals
        goal_rules = [
            {
                'days_before': 7,
                'subject_template': '⏰ Savings Goal Reminder: {goal_name} due in 7 days',
                'message_template': 'Your savings goal "{goal_name}" is due in 7 days.\n\n'
                                   'Target: ₹{target_amount}\n'
                                   'Saved: ₹{saved_amount}\n'
                                   'Progress: {progress}%\n\n'
                                   'You have {days_left} days left to reach your goal!'
            },
            {
                'days_before': 1,
                'subject_template': '📅 Savings Goal: {goal_name} due tomorrow',
                'message_template': 'Your savings goal "{goal_name}" is due tomorrow!\n\n'
                                   'Target: ₹{target_amount}\n'
                                   'Saved: ₹{saved_amount}\n'
                                   'Progress: {progress}%\n\n'
                                   'Final day to reach your target!'
            },
            {
                'days_before': 0,
                'subject_template': '🎯 Today: {goal_name} deadline',
                'message_template': 'Today is the deadline for your savings goal "{goal_name}"!\n\n'
                                   'Target: ₹{target_amount}\n'
                                   'Saved: ₹{saved_amount}\n'
                                   'Progress: {progress}%\n\n'
                                   'Complete your goal today!'
            },
            {
                'days_before': -1,
                'subject_template': '🚨 Overdue: {goal_name} goal deadline passed',
                'message_template': 'Your savings goal "{goal_name}" deadline has passed!\n\n'
                                   'Target: ₹{target_amount}\n'
                                   'Saved: ₹{saved_amount}\n'
                                   'Progress: {progress}%\n\n'
                                   'Please update your goal or mark as complete.'
            },
        ]
        
        # Default rules for recurring payments
        payment_rules = [
            {
                'days_before': 3,
                'subject_template': '⏰ Payment Reminder: {payment_name} due in 3 days',
                'message_template': 'Your {frequency} payment "{payment_name}" is due in 3 days.\n\n'
                                   'Amount: ₹{amount}\n'
                                   'Category: {category}\n'
                                   'Due Date: {due_date}\n\n'
                                   'Please ensure funds are available.'
            },
            {
                'days_before': 1,
                'subject_template': '📅 Payment Due Tomorrow: {payment_name}',
                'message_template': 'Your {frequency} payment "{payment_name}" is due tomorrow!\n\n'
                                   'Amount: ₹{amount}\n'
                                   'Category: {category}\n\n'
                                   'Scheduled for: {due_date}'
            },
            {
                'days_before': 0,
                'subject_template': '💳 Payment Due Today: {payment_name}',
                'message_template': 'Your {frequency} payment "{payment_name}" is due today!\n\n'
                                   'Amount: ₹{amount}\n'
                                   'Category: {category}\n\n'
                                   'Please make the payment today.'
            },
            {
                'days_before': -1,
                'subject_template': '🚨 Overdue Payment: {payment_name}',
                'message_template': 'Your {frequency} payment "{payment_name}" is overdue!\n\n'
                                   'Amount: ₹{amount}\n'
                                   'Category: {category}\n'
                                   'Was due on: {due_date}\n\n'
                                   'Please make the payment as soon as possible.'
            },
        ]
        
        # Create goal rules
        for rule_data in goal_rules:
            ReminderRule.objects.update_or_create(
                reminder_type='goal',
                days_before=rule_data['days_before'],
                defaults={
                    'subject_template': rule_data['subject_template'],
                    'message_template': rule_data['message_template'],
                    'enabled': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created/updated goal rule: {rule_data["days_before"]} days before'))
        
        # Create payment rules
        for rule_data in payment_rules:
            ReminderRule.objects.update_or_create(
                reminder_type='recurring',
                days_before=rule_data['days_before'],
                defaults={
                    'subject_template': rule_data['subject_template'],
                    'message_template': rule_data['message_template'],
                    'enabled': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created/updated payment rule: {rule_data["days_before"]} days before'))
        
        self.stdout.write(self.style.SUCCESS('Successfully setup all reminder rules!'))