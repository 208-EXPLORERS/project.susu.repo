from django.urls import path
from . import views
from django.contrib import admin
from .views import AddTransactionView, custom_login_view
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Authentication
    path('login/', custom_login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # Officer Dashboard
    path('officer_dashboard/', views.officer_dashboard, name='officer_dashboard'),
    
    # Customer Management
    path('officer/customers/', views.officer_customers, name='officer_customers'),
    path('officer/add_customer/', views.add_customer, name='add_customer'),
    path('officer/customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('officer/customer/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('officer/customer/<int:customer_id>/transactions/', views.customer_transactions, name='customer_transactions'),
    
    # Contributions
    path('officer/customer/<int:customer_id>/contribute/', views.add_contribution, name='add_contribution'),
    
    # Transactions
    path('officer/add_transaction/', AddTransactionView.as_view(), name='add_transaction'),
    
    # Loans
    path('officer/customer/<int:customer_id>/apply_loan/', views.apply_loan, name='apply_loan'),
    path('officer/loan/<int:loan_id>/repayment/', views.add_loan_repayment, name='add_loan_repayment'),
    
    # Daily Submissions
    path('officer/submit_daily_total/', views.submit_daily_total, name='submit_daily_total'),
    path('officer/submissions/', views.submission_history, name='submission_history'),
    
    # Admin - Loan Management
    path('admin/review_loans/', views.review_loans, name='review_loans'),
    path('admin/approve_loan/<int:loan_id>/', views.approve_loan, name='approve_loan'),
    path('admin/reject_loan/<int:loan_id>/', views.reject_loan, name='reject_loan'),
    path('admin/disburse_loan/<int:loan_id>/', views.disburse_loan, name='disburse_loan'),
    
    # Admin - Daily Submissions
    path('admin/review_submissions/', views.review_daily_submissions, name='review_submissions'),
    path('admin/approve_submission/<int:submission_id>/', views.approve_submission, name='approve_submission'),
    
    # Admin - Export
    path('admin/export/contributions/pdf/', views.export_contributions_pdf, name='export_contributions_pdf'),
    path('admin/export/contributions/csv/', views.export_contributions_csv, name='export_contributions_csv'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # API Endpoints
    path('api/notifications/unread-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('api/loan/<int:loan_id>/status/', views.check_loan_status, name='check_loan_status'),
    
    # Django Admin (keep at the end)
    path('admin/', admin.site.urls),
]