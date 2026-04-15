from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.group_create, name='group_create'),
    path('join/', views.group_join, name='group_join'),
    path('<int:group_id>/', views.group_dashboard, name='group_dashboard'),
    path('<int:group_id>/add-expense/', views.add_group_expense, name='add_group_expense'),
]
