import os
import django
from datetime import date, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from expenses.models import Expense
from expenses.analysis import SpendingAnalyzer

User = get_user_model()

def generate_test_data():
    """Generate test expense data for analysis"""
    user = User.objects.filter(username='testuser').first()
    if not user:
        user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')
        print(f"✅ Created test user: {user.username}")
    else:
        # Clear existing test data
        Expense.objects.filter(owner=user).delete()
        print(f"🧹 Cleared existing expenses for {user.username}")
    
    print(f"📊 Generating test data for {user.username}")
    
    categories = ['Food', 'Travel', 'Bills', 'Entertainment', 'Shopping', 'Healthcare']
    vendors = {
        'Food': ['Pizza Hut', 'Domino\'s', 'Starbucks', 'Local Cafe'],
        'Travel': ['Uber', 'Ola', 'Indian Oil', 'Railways'],
        'Bills': ['Electricity Board', 'Water Dept', 'Internet', 'Phone'],
        'Entertainment': ['Netflix', 'Amazon Prime', 'Movie Theater', 'Spotify'],
        'Shopping': ['Amazon', 'Flipkart', 'Mall', 'Local Market'],
        'Healthcare': ['Apollo Pharmacy', 'Clinic', 'Hospital', 'MedPlus']
    }
    
    # Generate 6 months of data
    today = date.today()
    expenses_created = 0
    
    for months_ago in range(5, -1, -1):  # 5 months ago to current
        month_date = today - timedelta(days=30 * months_ago)
        
        # Generate 15-25 expenses per month
        for _ in range(random.randint(15, 25)):
            category = random.choice(categories)
            vendor = random.choice(vendors[category])
            
            # Create seasonal patterns
            if category == 'Travel' and month_date.month in [12, 1, 5, 6]:  # Vacation months
                amount = random.uniform(1000, 5000)
            elif category == 'Bills' and month_date.month % 3 == 0:  # Quarterly bills
                amount = random.uniform(2000, 8000)
            elif category == 'Shopping' and month_date.month == 12:  # Holiday shopping
                amount = random.uniform(2000, 10000)
            else:
                amount = random.uniform(100, 2000)
            
            # Create expense
            expense_date = month_date.replace(day=random.randint(1, 28))
            Expense.objects.create(
                owner=user,
                amount=round(amount, 2),
                date=expense_date,
                vendor=vendor,
                description=f"{vendor} - {category}",
                category=category
            )
            expenses_created += 1
    
    print(f"✅ Generated {expenses_created} test expenses!")

def test_analyzer():
    """Test the spending analyzer"""
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        print("❌ Test user not found. Run generate_test_data() first.")
        return
    
    analyzer = SpendingAnalyzer(user)
    
    print("\n🔍 Testing Spending Analyzer")
    print("=" * 60)
    
    # Test monthly data
    print("\n📅 Monthly Data:")
    monthly = analyzer.get_monthly_data()
    if not monthly.empty:
        print(monthly.round(2))
    else:
        print("No data available")
    
    # Test trends
    print("\n📈 Month-over-Month Trends:")
    trends = analyzer.calculate_trends()
    if trends:
        for cat, data in trends.items():
            if cat != 'Total':
                direction_icon = "🔼" if data['direction'] == 'up' else "🔽" if data['direction'] == 'down' else "⏺️"
                print(f"  {cat}: {direction_icon} {data['change']}% (₹{data['previous']} → ₹{data['current']})")
    else:
        print("  No trend data available")
    
    # Test moving average
    print("\n📊 Moving Averages (3-month):")
    moving_avg = analyzer.calculate_moving_average()
    if moving_avg:
        for cat, data in moving_avg.items():
            if cat != 'Total' and data.get('current', 0) > 0:
                print(f"  {cat}: ₹{data['current']} ({data['trend']})")
    
    # Test anomalies
    print("\n⚠️ Detected Anomalies:")
    anomalies = analyzer.detect_anomalies()
    if anomalies:
        for anomaly in anomalies:
            print(f"  {anomaly['category']} in {anomaly['month']}: ₹{anomaly['amount']} (z-score: {anomaly['z_score']})")
    else:
        print("  No anomalies detected")
    
    # Test insights
    print("\n💡 Smart Insights:")
    insights = analyzer.generate_insights()
    if insights:
        for insight in insights:
            print(f"  {insight['message']}")
    else:
        print("  No insights generated")
    
    # Test category distribution
    print("\n🥧 Current Month Distribution:")
    distribution = analyzer.get_category_distribution()
    if distribution:
        for cat, data in distribution.items():
            print(f"  {cat}: ₹{data['amount']} ({data['percentage']}%)")
    
    # Test yearly comparison
    print("\n📅 Year-over-Year:")
    yearly = analyzer.get_yearly_comparison()
    print(f"  {yearly['last_year']}: ₹{yearly['last_total']}")
    print(f"  {yearly['current_year']}: ₹{yearly['current_total']}")
    if yearly['percent_change'] != 0:
        change_icon = "📈" if yearly['percent_change'] > 0 else "📉"
        print(f"  {change_icon} {yearly['percent_change']}% change")
    
    print("\n" + "=" * 60)
    print("✅ Analysis test complete!")

if __name__ == '__main__':
    print("🚀 Starting Spending Analysis Test")
    print("-" * 40)
    generate_test_data()
    test_analyzer()