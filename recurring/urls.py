from django.urls import path
from . import views

app_name = 'recurring'

urlpatterns = [
    path('', views.recurring_dashboard, name='dashboard'),
    path('add/', views.add_recurring_payment, name='add'),
    path('<int:payment_id>/edit/', views.edit_recurring_payment, name='edit'),
    path('<int:payment_id>/delete/', views.delete_recurring_payment, name='delete'),
    path('<int:payment_id>/toggle-active/', views.toggle_active, name='toggle_active'),
]