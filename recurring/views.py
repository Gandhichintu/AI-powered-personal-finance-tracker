from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.utils.timezone import now
from .models import RecurringPayment

@login_required
def recurring_dashboard(request):
    payments = RecurringPayment.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate stats
    total_monthly = sum(
        p.amount for p in payments 
        if p.frequency == 'monthly' and p.is_active
    )
    
    # Payments due this week (0-7 days from now)
    due_this_week = [
        p for p in payments 
        if p.is_active and 0 <= p.days_until_due() <= 7
    ]
    
    # Potential Savings: Identify subscription payments that could be optimized
    # For demonstration, we assume 10% savings on entertainment subscriptions
    potential_savings = sum(
        p.amount * Decimal('0.1') for p in payments 
        if p.category == 'subscription' and p.is_active
    )
    
    return render(request, 'recurring/dashboard.html', {
        'payments': payments,
        'total_monthly': total_monthly,
        'due_this_week_count': len(due_this_week),
        'due_this_week': due_this_week,
        'potential_savings': round(potential_savings, 2)
    })

@login_required
def add_recurring_payment(request):
    if request.method == 'POST':
        try:
            RecurringPayment.objects.create(
                user=request.user,
                name=request.POST['name'],
                amount=Decimal(request.POST['amount']),
                category=request.POST['category'],
                frequency=request.POST['frequency'],
                next_payment_date=request.POST['next_payment_date'],
                is_active=True
            )
            messages.success(request, 'Recurring payment added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding payment: {str(e)}')
    
    return redirect('recurring:dashboard')

@login_required
def edit_recurring_payment(request, payment_id):
    payment = get_object_or_404(RecurringPayment, id=payment_id, user=request.user)
    
    if request.method == 'POST':
        try:
            payment.name = request.POST.get('name', payment.name)
            payment.amount = Decimal(request.POST.get('amount', payment.amount))
            payment.category = request.POST.get('category', payment.category)
            payment.frequency = request.POST.get('frequency', payment.frequency)
            payment.next_payment_date = request.POST.get('next_payment_date', payment.next_payment_date)
            payment.save()
            messages.success(request, f'Payment "{payment.name}" updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating payment: {str(e)}')
    
    return redirect('recurring:dashboard')

@login_required
def delete_recurring_payment(request, payment_id):
    payment = get_object_or_404(RecurringPayment, id=payment_id, user=request.user)
    
    if request.method == 'POST':
        payment_name = payment.name
        payment.delete()
        messages.success(request, f'Payment "{payment_name}" deleted successfully!')
    
    return redirect('recurring:dashboard')

@login_required
def toggle_active(request, payment_id):
    payment = get_object_or_404(RecurringPayment, id=payment_id, user=request.user)
    
    payment.is_active = not payment.is_active
    payment.save()
    
    status = "activated" if payment.is_active else "paused"
    messages.success(request, f'Payment "{payment.name}" {status}!')
    
    return redirect('recurring:dashboard')