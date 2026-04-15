import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from expenses.models import MonthlyAggregate
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate synthetic historical expense data for predictions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='Username to generate data for'
        )
        parser.add_argument(
            '--months',
            type=int,
            default=24,
            help='Number of months of historical data to generate'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        months = options['months']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
            return
        
        self.stdout.write(f"📊 Generating {months} months of historical data for {username}")
        
        # Fix: Use 'ME' instead of 'M' for month-end frequency
        # Calculate start date (months ago)
        start_date = datetime.now().date() - timedelta(days=30 * months)
        
        # Generate date range with month-end frequency
        dates = pd.date_range(
            start=start_date,
            periods=months,
            freq='ME'  # Changed from 'M' to 'ME'
        )
        
        # Smart synthetic formula
        base = 15000
        trend = np.arange(months) * 300
        seasonality = 2000 * np.sin(np.arange(months) * (2 * np.pi / 12))
        noise = np.random.normal(0, 1000, months)
        
        expenses = base + trend + seasonality + noise
        expenses = np.maximum(expenses, 5000)  # Minimum 5000
        expenses = np.round(expenses, 0)
        
        # Generate category breakdowns
        categories = ['Food', 'Travel', 'Bills', 'Shopping', 'Entertainment', 'Healthcare']
        
        created_count = 0
        updated_count = 0
        
        for i, date in enumerate(dates):
            total = expenses[i]
            
            # Create realistic category distribution
            distribution = {}
            remaining = total
            
            # Food: 20-35%
            food_pct = np.random.uniform(0.20, 0.35)
            food_amt = total * food_pct
            distribution['Food'] = round(food_amt, 2)
            remaining -= food_amt
            
            # Bills: 15-25%
            bills_pct = np.random.uniform(0.15, 0.25)
            bills_amt = total * bills_pct
            distribution['Bills'] = round(bills_amt, 2)
            remaining -= bills_amt
            
            # Travel: 5-15%
            travel_pct = np.random.uniform(0.05, 0.15)
            travel_amt = total * travel_pct
            distribution['Travel'] = round(travel_amt, 2)
            remaining -= travel_amt
            
            # Shopping: 10-20%
            shopping_pct = np.random.uniform(0.10, 0.20)
            shopping_amt = total * shopping_pct
            distribution['Shopping'] = round(shopping_amt, 2)
            remaining -= shopping_amt
            
            # Entertainment: 5-10%
            entertainment_amt = total * np.random.uniform(0.05, 0.10)
            distribution['Entertainment'] = round(entertainment_amt, 2)
            remaining -= entertainment_amt
            
            # Healthcare: Rest
            distribution['Healthcare'] = round(remaining, 2)
            
            # Ensure no negative values
            for cat in distribution:
                if distribution[cat] < 0:
                    distribution[cat] = 0
            
            # Save or update
            month_first = date.replace(day=1)
            obj, created = MonthlyAggregate.objects.update_or_create(
                user=user,
                month=month_first,
                defaults={
                    'total_expense': Decimal(str(total)),
                    'categories': distribution
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Generated data: {created_count} created, {updated_count} updated'
        ))
        
        # Display summary
        aggregates = MonthlyAggregate.objects.filter(user=user).order_by('-month')
        if aggregates.exists():
            self.stdout.write("\n📈 Generated Monthly Data:")
            for agg in aggregates[:6]:  # Show last 6 months
                self.stdout.write(f"  {agg.month.strftime('%B %Y')}: ₹{agg.total_expense}")
            
            # Calculate statistics
            all_expenses = [float(agg.total_expense) for agg in aggregates]
            self.stdout.write(f"\n📊 Statistics:")
            self.stdout.write(f"  Average: ₹{np.mean(all_expenses):.0f}")
            self.stdout.write(f"  Min: ₹{np.min(all_expenses):.0f}")
            self.stdout.write(f"  Max: ₹{np.max(all_expenses):.0f}")