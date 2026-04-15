from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.utils.timezone import now
from .models import SavingsGoal

@login_required
def goals_dashboard(request):
    # Get all goals including completed ones
    goals = SavingsGoal.objects.filter(user=request.user).order_by('-created_at')
    
    # Separate active and completed goals
    active_goals = goals.filter(is_completed=False)
    completed_goals = goals.filter(is_completed=True)
    
    total_goals = goals.count()
    total_saved = sum(g.saved_amount for g in goals)
    
    # Find nearest deadline among active goals
    nearest_deadline = None
    if active_goals:
        nearest_deadline = active_goals.order_by('deadline').first()
    
    return render(request, 'goals/dashboard.html', {
        'active_goals': active_goals,
        'completed_goals': completed_goals,
        'total_goals': total_goals,
        'total_saved': total_saved,
        'nearest_deadline': nearest_deadline
    })

@login_required
def create_goal(request):
    if request.method == 'POST':
        try:
            goal = SavingsGoal.objects.create(
                user=request.user,
                name=request.POST['name'],
                target_amount=Decimal(request.POST['target_amount']),
                deadline=request.POST['deadline'],
                saved_amount=0
            )
            messages.success(request, f'Goal "{goal.name}" created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating goal: {str(e)}')
    
    return redirect('goals:goals_dashboard')

@login_required
def add_deposit(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            if amount > 0:
                goal.saved_amount += amount
                
                # Mark as completed if saved amount meets or exceeds target
                if goal.saved_amount >= goal.target_amount:
                    goal.is_completed = True
                    messages.success(request, f'Congratulations! Goal "{goal.name}" completed! 🎉')
                else:
                    messages.success(request, f'Deposited ₹{amount} to "{goal.name}"')
                
                goal.save()
            else:
                messages.error(request, 'Amount must be greater than 0')
        except Exception as e:
            messages.error(request, f'Error adding deposit: {str(e)}')
    
    return redirect('goals:goals_dashboard')

@login_required
def edit_goal(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        try:
            goal.name = request.POST.get('name', goal.name)
            goal.target_amount = Decimal(request.POST.get('target_amount', goal.target_amount))
            goal.deadline = request.POST.get('deadline', goal.deadline)
            goal.save()
            messages.success(request, f'Goal "{goal.name}" updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating goal: {str(e)}')
    
    return redirect('goals:goals_dashboard')

@login_required
def delete_goal(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        goal_name = goal.name
        goal.delete()
        messages.success(request, f'Goal "{goal_name}" deleted successfully!')
    
    return redirect('goals:goals_dashboard')

@login_required
def toggle_complete(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    
    goal.is_completed = not goal.is_completed
    goal.save()
    
    status = "completed" if goal.is_completed else "reactivated"
    messages.success(request, f'Goal "{goal.name}" marked as {status}!')
    
    return redirect('goals:goals_dashboard')