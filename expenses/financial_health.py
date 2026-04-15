from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Income, Debt, Asset, EmergencyFund, FinancialGoal
from .analysis import SpendingAnalyzer

class FinancialHealthAnalyzer:
    """Analyze user's financial health metrics"""
    
    def __init__(self, user):
        self.user = user
        self.analyzer = SpendingAnalyzer(user)
    
    def get_monthly_income(self):
        """Calculate average monthly income"""
        last_6_months = timezone.now().date() - timedelta(days=180)
        incomes = Income.objects.filter(
            user=self.user,
            date__gte=last_6_months
        )
        
        total = incomes.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        count = incomes.count()
        
        if count > 0:
            return total / Decimal(str(count))
        return Decimal('0')
    
    def get_monthly_expenses(self):
        """Get average monthly expenses"""
        monthly_data = self.analyzer.get_monthly_data()
        if not monthly_data.empty and 'Total' in monthly_data.columns:
            return Decimal(str(monthly_data['Total'].mean()))
        return Decimal('0')
    
    def get_savings_rate(self):
        """Calculate savings rate: (Income - Expenses) / Income * 100"""
        monthly_income = self.get_monthly_income()
        monthly_expenses = self.get_monthly_expenses()
        
        if monthly_income > 0:
            savings = monthly_income - monthly_expenses
            return float((savings / monthly_income) * 100)
        return 0.0
    
    def get_total_debt(self):
        """Calculate total outstanding debt - returns Decimal"""
        total = Debt.objects.filter(user=self.user, is_paid=False).aggregate(
            Sum('amount')
        )['amount__sum'] or Decimal('0')
        return total  # Return Decimal, not float
    
    def get_debt_to_income_ratio(self):
        """Calculate debt-to-income ratio (DTI) - returns float"""
        monthly_income = self.get_monthly_income()
        total_debt = self.get_total_debt()
        
        if monthly_income > 0:
            # Convert to float for calculation
            annual_income = float(monthly_income) * 12
            debt_amount = float(total_debt)
            
            if annual_income > 0:
                return (debt_amount / annual_income) * 100
        return 0.0
    
    def get_net_worth(self):
        """Calculate net worth: Assets - Debts - returns float"""
        total_assets = Asset.objects.filter(user=self.user).aggregate(
            Sum('value')
        )['value__sum'] or Decimal('0')
        total_debts = self.get_total_debt()
        
        return float(total_assets) - float(total_debts)
    
    def get_emergency_fund_status(self):
        """Get emergency fund status"""
        try:
            ef = EmergencyFund.objects.get(user=self.user)
            monthly_expenses = self.get_monthly_expenses()
            months_covered = ef.months_covered() if monthly_expenses > 0 else 0
            
            status = {
                'current': float(ef.current_amount),
                'target': float(ef.target_amount),
                'months_covered': float(months_covered) if months_covered else 0.0,
                'target_months': ef.target_months,
                'progress': float(ef.progress_percentage()),
                'is_adequate': months_covered >= ef.target_months
            }
            return status
        except EmergencyFund.DoesNotExist:
            return None
    
    def get_financial_health_score(self):
        """Calculate overall financial health score (0-100)"""
        scores = []
        weights = []
        
        # Savings rate score (0-100)
        savings_rate = self.get_savings_rate()
        if savings_rate >= 20:
            savings_score = 100
        elif savings_rate >= 10:
            savings_score = 70
        elif savings_rate >= 5:
            savings_score = 50
        elif savings_rate > 0:
            savings_score = 30
        else:
            savings_score = 0
        scores.append(savings_score)
        weights.append(0.3)  # 30% weight
        
        # Debt-to-income score (0-100)
        dti = self.get_debt_to_income_ratio()
        if dti <= 15:
            debt_score = 100
        elif dti <= 30:
            debt_score = 70
        elif dti <= 40:
            debt_score = 40
        else:
            debt_score = 10
        scores.append(debt_score)
        weights.append(0.25)  # 25% weight
        
        # Emergency fund score (0-100)
        ef_status = self.get_emergency_fund_status()
        if ef_status:
            if ef_status['is_adequate']:
                ef_score = 100
            else:
                ef_score = int(ef_status['progress'])
        else:
            ef_score = 0
        scores.append(ef_score)
        weights.append(0.25)  # 25% weight
        
        # Net worth trend score (0-100)
        net_worth = self.get_net_worth()
        if net_worth > 0:
            net_score = min(100.0, net_worth / 100000.0)  # Cap at 100 for 100k+
        else:
            net_score = 0
        scores.append(net_score)
        weights.append(0.2)  # 20% weight
        
        # Weighted average
        total_score = sum(s * w for s, w in zip(scores, weights))
        return round(total_score, 1)
    
    def generate_health_insights(self):
        """Generate actionable insights"""
        insights = []
        
        # Savings rate insight
        savings_rate = self.get_savings_rate()
        if savings_rate < 10:
            insights.append({
                'type': 'savings',
                'icon': '💰',
                'priority': 'high',
                'message': f'Your savings rate is only {savings_rate:.1f}%. Aim for 20% to build wealth faster.',
                'action': 'Try to reduce unnecessary expenses by 5-10% next month.'
            })
        elif savings_rate >= 20:
            insights.append({
                'type': 'savings',
                'icon': '🎉',
                'priority': 'low',
                'message': f'Great savings rate of {savings_rate:.1f}%! You\'re on track for financial freedom.',
                'action': 'Consider investing your surplus in long-term assets.'
            })
        
        # Debt insight
        dti = self.get_debt_to_income_ratio()
        if dti > 40:
            insights.append({
                'type': 'debt',
                'icon': '⚠️',
                'priority': 'high',
                'message': f'Your debt-to-income ratio is {dti:.1f}%. This is concerning.',
                'action': 'Create a debt repayment plan. Consider debt consolidation.'
            })
        elif dti > 30:
            insights.append({
                'type': 'debt',
                'icon': '📊',
                'priority': 'medium',
                'message': f'Debt-to-income ratio is {dti:.1f}%. Above recommended 30%.',
                'action': 'Focus on paying down high-interest debt first.'
            })
        
        # Emergency fund insight
        ef_status = self.get_emergency_fund_status()
        if ef_status:
            if not ef_status['is_adequate']:
                months_needed = ef_status['target_months'] - ef_status['months_covered']
                insights.append({
                    'type': 'emergency',
                    'icon': '🛡️',
                    'priority': 'high',
                    'message': f'Emergency fund covers only {ef_status["months_covered"]:.1f} months.',
                    'action': f'Need ₹{ef_status["target"] - ef_status["current"]:.0f} more for {ef_status["target_months"]} months of expenses.'
                })
            else:
                insights.append({
                    'type': 'emergency',
                    'icon': '✅',
                    'priority': 'low',
                    'message': f'Excellent! Your emergency fund covers {ef_status["months_covered"]:.1f} months.',
                    'action': 'Consider investing extra savings for higher returns.'
                })
        
        return insights
    
    def get_financial_summary(self):
        """Get complete financial summary"""
        monthly_income = self.get_monthly_income()
        monthly_expenses = self.get_monthly_expenses()
        savings_rate = self.get_savings_rate()
        
        return {
            'monthly_income': float(monthly_income),
            'monthly_expenses': float(monthly_expenses),
            'monthly_savings': float(monthly_income - monthly_expenses),
            'savings_rate': savings_rate,
            'total_debt': float(self.get_total_debt()),
            'debt_to_income_ratio': self.get_debt_to_income_ratio(),
            'net_worth': self.get_net_worth(),
            'financial_health_score': self.get_financial_health_score(),
            'emergency_fund': self.get_emergency_fund_status(),
        }