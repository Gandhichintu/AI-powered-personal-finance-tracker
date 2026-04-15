from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
from .models import Group, GroupMember, GroupExpense, GroupExpenseShare
from django.contrib import messages

@login_required
def group_list(request):
    groups = Group.objects.filter(members__user=request.user)
    return render(request, 'groups/group_list.html', {'groups': groups})


@login_required
def group_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group = Group.objects.create(name=name, created_by=request.user)
            GroupMember.objects.create(group=group, user=request.user)
            messages.success(request, f'Group "{name}" created successfully!')
            return redirect('groups:group_list')
        else:
            messages.error(request, 'Group name is required')
    
    return render(request, 'groups/group_create.html')


@login_required
def group_join(request):
    error = None
    if request.method == 'POST':
        code = request.POST.get('invite_code', '').strip()
        try:
            group = Group.objects.get(invite_code=code)
            member, created = GroupMember.objects.get_or_create(
                group=group, 
                user=request.user
            )
            if created:
                messages.success(request, f'Successfully joined group "{group.name}"')
            else:
                messages.info(request, f'You are already a member of "{group.name}"')
            return redirect('groups:group_list')
        except Group.DoesNotExist:
            error = 'Invalid invite code. Please check and try again.'
            messages.error(request, error)
    
    return render(request, 'groups/group_join.html', {'error': error})


@login_required
def group_dashboard(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member of this group
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, 'You are not a member of this group')
        return redirect('groups:group_list')
    
    expenses = group.expenses.all().order_by('-date')
    members = group.members.all()

    # Calculate balances
    balances = {}
    balance_display = {}
    for member in members:
        balances[member.user] = Decimal('0.00')

    for expense in expenses:
        paid_by = expense.paid_by
        total = expense.amount
        shares = expense.shares.all()
        for share in shares:
            balances[share.user] -= share.share_amount
        balances[paid_by] += total

    # Create display dictionary with absolute values for negative amounts
    for user, bal in balances.items():
        if bal < 0:
            balance_display[user] = {
                'amount': abs(bal),
                'is_positive': False,
                'display': f'Owes ₹{abs(bal)}'
            }
        elif bal > 0:
            balance_display[user] = {
                'amount': bal,
                'is_positive': True,
                'display': f'Gets ₹{bal}'
            }
        else:
            balance_display[user] = {
                'amount': bal,
                'is_positive': None,
                'display': 'Settled'
            }

    return render(request, 'groups/group_dashboard.html', {
        'group': group,
        'expenses': expenses,
        'balances': balances,
        'balance_display': balance_display,  # NEW
        'members': members

    })


@login_required
def add_group_expense(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, 'You are not a member of this group')
        return redirect('groups:group_list')

    if request.method == 'POST':
        try:
            desc = request.POST['description']
            amount = Decimal(request.POST['amount'])
            category = request.POST.get('category', 'Other')
            paid_by_id = request.POST['paid_by']
            date = request.POST['date']
            
            # Validate amount
            if amount <= 0:
                messages.error(request, 'Amount must be greater than 0')
                return redirect('groups:group_dashboard', group_id=group.id)

            # Create expense
            expense = GroupExpense.objects.create(
                group=group,
                description=desc,
                amount=amount,
                category=category,
                paid_by_id=paid_by_id,
                date=date
            )

            # Split equally among members
            members = group.members.all()
            split = amount / members.count()
            
            for member in members:
                GroupExpenseShare.objects.create(
                    expense=expense,
                    user=member.user,
                    share_amount=split.quantize(Decimal('0.01'))  # Round to 2 decimal places
                )

            messages.success(request, f'Expense "{desc}" added successfully!')
            return redirect('groups:group_dashboard', group_id=group.id)
            
        except Exception as e:
            messages.error(request, f'Error adding expense: {str(e)}')
    
    return redirect('groups:group_dashboard', group_id=group.id)