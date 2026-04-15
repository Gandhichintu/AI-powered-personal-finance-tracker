from django.core.management.base import BaseCommand
from django.utils import timezone
from reminders.cron import send_due_reminders, generate_future_reminders

class Command(BaseCommand):
    help = 'Run cron jobs manually'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--job',
            type=str,
            choices=['send', 'generate', 'all'],
            default='all',
            help='Which cron job to run'
        )
    
    def handle(self, *args, **options):
        job = options['job']
        
        self.stdout.write(f"Starting cron jobs at {timezone.now()}")
        
        if job in ['send', 'all']:
            self.stdout.write("Running send_due_reminders...")
            result = send_due_reminders()
            self.stdout.write(self.style.SUCCESS(f"Result: {result}"))
        
        if job in ['generate', 'all']:
            self.stdout.write("Running generate_future_reminders...")
            result = generate_future_reminders()
            self.stdout.write(self.style.SUCCESS(f"Result: {result}"))
        
        self.stdout.write(self.style.SUCCESS("Cron jobs completed!"))