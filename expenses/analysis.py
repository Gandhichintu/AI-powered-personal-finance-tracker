import pandas as pd
import numpy as np
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
from .models import Expense
import calendar

class SpendingAnalyzer:
    """Analyze spending patterns and generate insights"""
    
    def __init__(self, user):
        self.user = user
        self.expenses = Expense.objects.filter(owner=user)
        
    def get_monthly_data(self, months=12):
        """Get monthly expense data for the last N months"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30 * months)
        
        # Query expenses in date range
        expenses = self.expenses.filter(date__gte=start_date, date__lte=end_date)
        
        if not expenses.exists():
            return pd.DataFrame()
        
        # Convert to DataFrame and handle Decimal conversion
        expense_list = []
        for exp in expenses:
            expense_list.append({
                'date': exp.date,
                'amount': float(exp.amount),  # Convert Decimal to float
                'category': exp.category
            })
        
        df = pd.DataFrame(expense_list)
        df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
        
        # Aggregate by month and category
        monthly = df.groupby(['month', 'category'])['amount'].sum().reset_index()
        
        # Pivot for easier analysis
        pivot = monthly.pivot(index='month', columns='category', values='amount').fillna(0)
        
        # Add total column
        pivot['Total'] = pivot.sum(axis=1)
        
        return pivot
    
    def calculate_trends(self):
        """Calculate month-over-month trends"""
        monthly_data = self.get_monthly_data()
        
        if monthly_data.empty or len(monthly_data) < 2:
            return {}
        
        trends = {}
        current_month = monthly_data.iloc[-1]
        previous_month = monthly_data.iloc[-2] if len(monthly_data) >= 2 else None
        
        if previous_month is not None:
            for category in monthly_data.columns:
                curr = current_month[category]
                prev = previous_month[category]
                
                if prev > 0:
                    change = ((curr - prev) / prev) * 100
                elif curr > 0:
                    change = 100  # New spending category
                else:
                    change = 0
                
                trends[category] = {
                    'current': round(curr, 2),
                    'previous': round(prev, 2),
                    'change': round(change, 1),
                    'direction': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
        
        return trends
    
    def calculate_moving_average(self, window=3):
        """Calculate 3-month moving average"""
        monthly_data = self.get_monthly_data()
        
        if monthly_data.empty or len(monthly_data) < window:
            return {}
        
        moving_avg = {}
        for category in monthly_data.columns:
            values = monthly_data[category].values.astype(float)  # Convert to float
            if len(values) >= window:
                ma = np.convolve(values, np.ones(window)/window, mode='valid')
                moving_avg[category] = {
                    'values': [round(float(x), 2) for x in ma],  # Convert to float and round
                    'current': round(float(ma[-1]), 2) if len(ma) > 0 else 0,
                    'trend': 'increasing' if len(ma) > 1 and ma[-1] > ma[-2] else 'decreasing' if len(ma) > 1 else 'stable'
                }
        
        return moving_avg
    
    def detect_anomalies(self, threshold=2.0):
        """Detect unusual spending patterns (2 standard deviations from mean)"""
        monthly_data = self.get_monthly_data(months=6)
        
        if monthly_data.empty or len(monthly_data) < 3:
            return []
        
        anomalies = []
        for category in monthly_data.columns:
            if category == 'Total':
                continue
                
            values = monthly_data[category].values.astype(float)  # Convert to float
            if len(values) > 0:
                mean = np.mean(values)
                std = np.std(values)
                
                if std > 0:
                    z_scores = [(v - mean) / std for v in values]
                    
                    for i, z in enumerate(z_scores):
                        if abs(z) > threshold:
                            anomalies.append({
                                'category': category,
                                'month': str(monthly_data.index[i]),
                                'amount': round(float(values[i]), 2),
                                'z_score': round(float(z), 2),
                                'severity': 'high' if abs(z) > 3 else 'medium'
                            })
        
        return anomalies
    
    def generate_insights(self):
        """Generate natural language insights"""
        trends = self.calculate_trends()
        moving_avg = self.calculate_moving_average()
        anomalies = self.detect_anomalies()
        
        insights = []
        
        # Top spending categories
        monthly_data = self.get_monthly_data()
        if not monthly_data.empty:
            current_month = monthly_data.iloc[-1]
            # Filter out Total and get top 3
            top_categories = current_month.drop('Total' if 'Total' in current_month.index else []).nlargest(3)
            
            if not top_categories.empty:
                categories_list = ', '.join([f"{cat} (₹{amt:.0f})" for cat, amt in top_categories.items()])
                insights.append({
                    'type': 'top_spending',
                    'message': f"📊 Your top spending categories this month: {categories_list}",
                    'icon': '📊',
                    'priority': 'high'
                })
        
        # MoM changes
        significant_changes = []
        for category, data in trends.items():
            if category != 'Total' and abs(data['change']) > 20:
                direction = "⬆️ increased" if data['direction'] == 'up' else "⬇️ decreased"
                significant_changes.append(
                    f"{category} {direction} by {abs(data['change'])}% "
                    f"(₹{data['previous']} → ₹{data['current']})"
                )
        
        if significant_changes:
            insights.append({
                'type': 'significant_changes',
                'message': "📈 Significant changes: " + "; ".join(significant_changes[:2]),
                'icon': '📈',
                'priority': 'medium'
            })
        
        # Anomalies
        for anomaly in anomalies[:2]:
            insights.append({
                'type': 'anomaly',
                'message': f"⚠️ Unusual spending in {anomaly['category']}: ₹{anomaly['amount']} "
                          f"({anomaly['severity']} deviation)",
                'icon': '⚠️',
                'priority': 'high' if anomaly['severity'] == 'high' else 'medium'
            })
        
        # Moving average trends
        for category, data in moving_avg.items():
            if category != 'Total' and data.get('trend') == 'increasing' and data.get('current', 0) > 1000:
                insights.append({
                    'type': 'trend',
                    'message': f"📉 Your {category} spending shows an increasing trend "
                              f"(3-month avg: ₹{data['current']})",
                    'icon': '📉',
                    'priority': 'medium'
                })
                break  # Just show one trend insight
        
        # Savings opportunity
        if not monthly_data.empty and 'Total' in monthly_data.columns:
            total_spent = monthly_data['Total'].sum()
            avg_monthly = monthly_data['Total'].mean()
            if avg_monthly > 0:
                savings_potential = round(avg_monthly * 0.1, 2)  # 10% potential savings
                insights.append({
                    'type': 'savings',
                    'message': f"💰 Potential savings: Reducing discretionary spending by 10% "
                              f"could save ~₹{savings_potential}/month",
                    'icon': '💰',
                    'priority': 'low'
                })
        
        return insights
    
    def get_category_distribution(self):
        """Get current month's category distribution"""
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        expenses = self.expenses.filter(date__gte=start_of_month, date__lte=today)
        
        if not expenses.exists():
            return {}
        
        # Convert Decimal to float
        distribution = {}
        for exp in expenses:
            cat = exp.category
            amount = float(exp.amount)
            if cat in distribution:
                distribution[cat] += amount
            else:
                distribution[cat] = amount
        
        # Calculate percentages
        total = sum(distribution.values())
        if total > 0:
            for cat in list(distribution.keys()):
                distribution[cat] = {
                    'amount': round(distribution[cat], 2),
                    'percentage': round((distribution[cat] / total) * 100, 1)
                }
        
        return distribution
    
    def get_yearly_comparison(self):
        """Compare current year vs previous year"""
        current_year = timezone.now().year
        last_year = current_year - 1
        
        current_year_expenses = self.expenses.filter(date__year=current_year)
        last_year_expenses = self.expenses.filter(date__year=last_year)
        
        current_total = float(current_year_expenses.aggregate(Sum('amount'))['amount__sum'] or 0)
        last_total = float(last_year_expenses.aggregate(Sum('amount'))['amount__sum'] or 0)
        
        comparison = {
            'current_year': current_year,
            'last_year': last_year,
            'current_total': round(current_total, 2),
            'last_total': round(last_total, 2),
            'difference': round(current_total - last_total, 2),
        }
        
        if last_total > 0:
            comparison['percent_change'] = round(((current_total - last_total) / last_total) * 100, 1)
        else:
            comparison['percent_change'] = 0
        
        return comparison