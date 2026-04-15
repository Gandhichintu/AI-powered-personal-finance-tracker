import os
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from expenses.models import Expense
from expenses.anomaly_detector import AnomalyDetector

def create_test_anomalies():
    """Create test data with anomalies"""
    user = get_user_model().objects.get(username='testuser')
    
    print("🧪 Creating test data with anomalies...")
    
    # Create normal expenses (random around 1000)
    for i in range(50):
        Expense.objects.create(
            owner=user,
            amount=random.uniform(500, 1500),
            date=date.today() - timedelta(days=random.randint(1, 90)),
            vendor=f'Store {i}',
            description='Normal expense',
            category='Food'
        )
    
    # Create anomaly (very high expense)
    Expense.objects.create(
        owner=user,
        amount=12000,
        date=date.today() - timedelta(days=2),
        vendor='Expensive Restaurant',
        description='Anomaly test',
        category='Food'
    )
    
    print("✅ Test data created!")
    
    # Run detection
    detector = AnomalyDetector(user)
    anomalies = detector.detect_anomalies(threshold=2.0)
    
    print(f"\n🔍 Detected {len(anomalies)} anomalies:")
    for a in anomalies:
        print(f"  - {a['reason']}")
        print(f"    Z-Score: {a['zscore']:.2f}")

if __name__ == '__main__':
    create_test_anomalies()