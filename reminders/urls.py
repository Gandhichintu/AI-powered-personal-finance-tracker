from django.urls import path
from . import views

app_name = 'reminders'

urlpatterns = [
    path('', views.notifications, name='notifications'),
    path('<uuid:reminder_id>/read/', views.mark_as_read, name='mark_as_read'),
    path('<uuid:reminder_id>/clear/', views.clear_notification, name='clear_notification'),
    path('clear-all/', views.clear_all_notifications, name='clear_all'),
]