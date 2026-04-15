"""
URL configuration for finance_tracker project.
"""
# finance_tracker/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Landing page as home
    path('', TemplateView.as_view(template_name='landing.html'), name='home'),
    # Accounts URLs
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout
    # Expenses URLs (dashboard and all expense-related pages)
    path('', include('expenses.urls', namespace='expenses')),
    # Other apps
    path('groups/', include('groups.urls')),
    path('goals/', include('goals.urls')),
    path('recurring/', include('recurring.urls')), 
    path('notifications/', include('reminders.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)