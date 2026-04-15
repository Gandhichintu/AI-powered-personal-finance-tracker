from django.contrib import admin
from .models import Group, GroupMember, GroupExpense, GroupExpenseShare

admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(GroupExpense)
admin.site.register(GroupExpenseShare)
