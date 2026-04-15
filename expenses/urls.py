# expenses/urls.py
from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Dashboard - main dashboard page
    path('dashboard/', views.dashboard, name='dashboard'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_add'),
    path('expenses/<int:pk>/edit/', views.expense_update, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('receipts/upload/', views.receipt_upload, name='receipt_upload'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/capture/', views.receipt_capture, name='receipt_capture'),
    path('receipts/capture/image/', views.capture_image, name='capture_image'),
    path('expenses/voice-input/', views.voice_input, name='voice_input'),
    path('expenses/voice-test/', views.voice_test, name='voice_test'), 
    path('api/predict-category/', views.predict_category, name='predict_category'),
    path('analysis/', views.analysis_dashboard, name='analysis_dashboard'),
    path('api/analysis-data/', views.analysis_data_api, name='analysis_data_api'),
    path('api/category-pie-data/', views.category_pie_data_api, name='category_pie_data_api'),
    path('export-analysis/', views.export_analysis_report, name='export_analysis'),
    path('anomalies/', views.anomaly_dashboard, name='anomaly_dashboard'),
    path('anomalies/<int:expense_id>/', views.anomaly_detail, name='anomaly_detail'),
    path('anomalies/<int:expense_id>/review/', views.mark_anomaly_reviewed, name='mark_anomaly_reviewed'),
    path('anomalies/<int:expense_id>/dismiss/', views.dismiss_anomaly, name='dismiss_anomaly'),
    path('api/anomaly-data/', views.anomaly_data_api, name='anomaly_data_api'),
    path('predictions/', views.prediction_dashboard, name='prediction_dashboard'),
    path('api/predictions/', views.prediction_api, name='prediction_api'),
    path('refresh-monthly-data/', views.refresh_monthly_data, name='refresh_monthly_data'),
    # Financial Health URLs
    path('financial-health/', views.financial_health_dashboard, name='financial_health'),
    path('financial-health/add-income/', views.add_income, name='add_income'),
    path('financial-health/add-debt/', views.add_debt, name='add_debt'),
    path('financial-health/add-asset/', views.add_asset, name='add_asset'),
    path('financial-health/setup-emergency/', views.setup_emergency_fund, name='setup_emergency'),
    path('financial-health/add-goal/', views.add_financial_goal, name='add_financial_goal'),
    path('financial-health/update-emergency/', views.update_emergency_fund, name='update_emergency'),
]