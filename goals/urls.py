from django.urls import path
from . import views

app_name = 'goals'

urlpatterns = [
    path('', views.goals_dashboard, name='goals_dashboard'),
    path('create/', views.create_goal, name='create_goal'),
    path('<int:goal_id>/deposit/', views.add_deposit, name='add_deposit'),
    path('<int:goal_id>/edit/', views.edit_goal, name='edit_goal'),
    path('<int:goal_id>/delete/', views.delete_goal, name='delete_goal'),
    path('<int:goal_id>/toggle-complete/', views.toggle_complete, name='toggle_complete'),
]