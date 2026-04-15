from django import forms
from .models import Expense, Receipt, Income, Debt, Asset, EmergencyFund, FinancialGoal

# In expenses/forms.py
class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'date', 'vendor', 'category', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border rounded px-3 py-2'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border rounded px-3 py-2'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01'}),
            'vendor': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'category': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2', 'id': 'id_category'}),
        }
class ReceiptUploadForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['image']


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['amount', 'date', 'source', 'income_type', 'description', 'is_recurring']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border rounded px-3 py-2'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01'}),
            'source': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2', 'placeholder': 'e.g., Salary, Freelance'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'w-full border rounded px-3 py-2'}),
            'income_type': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-checkbox h-4 w-4 text-blue-600'}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")
        return amount

class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = ['name', 'amount', 'interest_rate', 'monthly_payment', 'due_date', 'debt_type', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2', 'placeholder': 'e.g., Credit Card, Home Loan'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01', 'placeholder': 'Annual interest rate %'}),
            'monthly_payment': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01', 'placeholder': 'Minimum monthly payment'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border rounded px-3 py-2'}),
            'debt_type': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'w-full border rounded px-3 py-2', 'placeholder': 'Additional notes...'}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")
        return amount

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['name', 'value', 'asset_type', 'purchase_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2', 'placeholder': 'e.g., Savings Account, Car, House'}),
            'value': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01'}),
            'asset_type': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border rounded px-3 py-2'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'w-full border rounded px-3 py-2'}),
        }
    
    def clean_value(self):
        value = self.cleaned_data.get('value')
        if value and value <= 0:
            raise forms.ValidationError("Value must be greater than 0")
        return value

class EmergencyFundForm(forms.ModelForm):
    class Meta:
        model = EmergencyFund
        fields = ['target_amount', 'target_months']
        widgets = {
            'target_amount': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01', 'placeholder': 'Target amount in ₹'}),
            'target_months': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'min': 1, 'max': 12, 'placeholder': 'Months of expenses to cover'}),
        }
    
    def clean_target_amount(self):
        amount = self.cleaned_data.get('target_amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Target amount must be greater than 0")
        return amount

class FinancialGoalForm(forms.ModelForm):
    class Meta:
        model = FinancialGoal
        fields = ['name', 'target_amount', 'deadline', 'goal_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2', 'placeholder': 'e.g., Buy a house, Retirement fund'}),
            'target_amount': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.01'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border rounded px-3 py-2'}),
            'goal_type': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
        }
    
    def clean_target_amount(self):
        amount = self.cleaned_data.get('target_amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Target amount must be greater than 0")
        return amount