import numpy as np
from datetime import timedelta, date
from django.db.models import Avg, StdDev, Count, Q
from django.utils import timezone
from collections import defaultdict
from .models import Expense
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect unusual spending patterns using Z-Score method"""
    
    def __init__(self, user):
        self.user = user
        self.expenses = Expense.objects.filter(owner=user)
        
    def calculate_category_stats(self, days=90):
        """Calculate mean and standard deviation for each category"""
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        stats = {}
        categories = [choice[0] for choice in Expense.CATEGORY_CHOICES]
        
        for category in categories:
            # Get expenses for this category in the time period
            category_expenses = self.expenses.filter(
                category=category,
                date__gte=cutoff_date
            ).values_list('amount', flat=True)
            
            amounts = [float(x) for x in category_expenses]  # Convert Decimal to float
            
            if len(amounts) >= 3:  # Need at least 3 data points
                mean = np.mean(amounts)
                std = np.std(amounts)
                stats[category] = {
                    'mean': mean,
                    'std': std,
                    'count': len(amounts),
                    'min': min(amounts),
                    'max': max(amounts)
                }
            else:
                # Not enough data, use global stats or defaults
                stats[category] = {
                    'mean': 0,
                    'std': 0,
                    'count': len(amounts),
                    'min': 0,
                    'max': 0
                }
        
        return stats
    
    def calculate_zscore(self, amount, mean, std):
        """Calculate Z-Score for an amount"""
        if std == 0:
            return 0
        return (amount - mean) / std
    
    def detect_anomalies(self, threshold=2.0, days=90):
        """
        Detect anomalies using Z-Score method
        threshold: Z-Score threshold (default 2.0 = 2 standard deviations)
        """
        stats = self.calculate_category_stats(days)
        anomalies = []
        
        # Get recent expenses not yet analyzed
        cutoff_date = timezone.now().date() - timedelta(days=30)
        recent_expenses = self.expenses.filter(
            date__gte=cutoff_date,
            is_anomaly=False
        ).order_by('-date')
        
        for expense in recent_expenses:
            category = expense.category
            amount = float(expense.amount)
            
            cat_stats = stats.get(category, {'mean': 0, 'std': 0})
            
            if cat_stats['std'] > 0 and cat_stats['count'] >= 3:
                zscore = self.calculate_zscore(amount, cat_stats['mean'], cat_stats['std'])
                
                # Check if it's an anomaly
                if abs(zscore) > threshold:
                    direction = "high" if amount > cat_stats['mean'] else "low"
                    
                    anomaly_info = {
                        'expense': expense,
                        'category': category,
                        'amount': amount,
                        'mean': cat_stats['mean'],
                        'std': cat_stats['std'],
                        'zscore': zscore,
                        'direction': direction,
                        'severity': 'high' if abs(zscore) > 3 else 'medium',
                        'reason': self.generate_reason(expense, cat_stats, zscore)
                    }
                    
                    anomalies.append(anomaly_info)
                    
                    # Update expense with anomaly info
                    expense.is_anomaly = True
                    expense.anomaly_score = zscore
                    expense.anomaly_reason = anomaly_info['reason']
                    expense.save()
                    
                    logger.info(f"Anomaly detected: {expense} - Z-Score: {zscore:.2f}")
        
        return anomalies
    
    def generate_reason(self, expense, stats, zscore):
        """Generate human-readable reason for anomaly"""
        amount = float(expense.amount)
        
        if amount > stats['mean']:
            multiplier = amount / stats['mean']
            if multiplier > 3:
                return f"🚨 This {expense.category} expense is {multiplier:.1f}x higher than your average of ₹{stats['mean']:.0f}"
            elif multiplier > 2:
                return f"⚠️ This {expense.category} expense is {multiplier:.1f}x higher than your average of ₹{stats['mean']:.0f}"
            else:
                return f"⚠️ This {expense.category} expense (₹{amount:.0f}) is above your average of ₹{stats['mean']:.0f}"
        else:
            return f"ℹ️ This {expense.category} expense (₹{amount:.0f}) is below your average of ₹{stats['mean']:.0f}"
    
    def get_recent_anomalies(self, days=7):
        """Get anomalies from recent days"""
        cutoff = timezone.now().date() - timedelta(days=days)
        return self.expenses.filter(
            is_anomaly=True,
            date__gte=cutoff,
            reviewed=False
        ).order_by('-date', '-anomaly_score')
    
    def get_anomaly_stats(self):
        """Get statistics about anomalies"""
        total_anomalies = self.expenses.filter(is_anomaly=True).count()
        unreviewed = self.expenses.filter(is_anomaly=True, reviewed=False).count()
        
        # Anomalies by category
        by_category = self.expenses.filter(
            is_anomaly=True
        ).values('category').annotate(
            count=Count('id'),
            avg_score=Avg('anomaly_score')
        ).order_by('-count')
        
        # Severe anomalies (Z-score > 3)
        severe = self.expenses.filter(
            is_anomaly=True,
            anomaly_score__gt=3
        ).count()
        
        return {
            'total': total_anomalies,
            'unreviewed': unreviewed,
            'severe': severe,
            'by_category': list(by_category)
        }
    
    def get_anomaly_timeline(self, months=6):
        """Get anomaly trend over time"""
        from django.db.models.functions import TruncMonth
        
        return self.expenses.filter(
            is_anomaly=True
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')[:months]
    
    def get_category_insights(self, category):
        """Get detailed insights for a specific category"""
        stats = self.calculate_category_stats()
        cat_stats = stats.get(category, {})
        
        recent = self.expenses.filter(
            category=category
        ).order_by('-date')[:10]
        
        anomalies = self.expenses.filter(
            category=category,
            is_anomaly=True
        ).order_by('-date')[:5]
        
        return {
            'stats': cat_stats,
            'recent': recent,
            'anomalies': anomalies,
            'total_count': self.expenses.filter(category=category).count(),
            'total_amount': sum(float(x.amount) for x in self.expenses.filter(category=category))
        }