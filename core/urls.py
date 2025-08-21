from django.urls import path
from . import views
from django.contrib import admin
from .views import AddTransactionView,custom_login_view
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static




urlpatterns = [
    path('admin/', views.dashboard, name='dashboard'),
    path('officer/add_transaction/', AddTransactionView.as_view(), name='add_transaction'),
    # Home/dashboard after login
    path('officer/customers/', views.officer_customers, name='officer_customers'),
    path('officer/add_customer/', views.add_customer, name='add_customer'),
    path('officer/customer/<int:customer_id>/transactions/', views.customer_transactions, name='customer_transactions'),
    #path('officer/submit_daily_total/', views.submit_daily_total, name='submit_daily_total'),
    path('admin/review_submissions/', views.review_daily_submissions, name='review_submissions'),
    path('admin/approve_submission/<int:submission_id>/', views.approve_submission, name='approve_submission'),
    #path('admin/', admin.site.urls),  # This must be present
    path('officer/customer/<int:customer_id>/contribute/', views.add_contribution, name='add_contribution'),
    path('officer/submissions/', views.submission_history, name='submission_history'),
    path('officer/customer/<int:customer_id>/apply_loan/', views.apply_loan, name='apply_loan'),
    path('admin/review_loans/', views.review_loans, name='review_loans'),
    path('admin/approve_loan/<int:loan_id>/', views.approve_loan, name='approve_loan'),
    path('admin/reject_loan/<int:loan_id>/', views.reject_loan, name='reject_loan'),
    path('admin/export/contributions/pdf/', views.export_contributions_pdf, name='export_contributions_pdf'),
    path('admin/export/contributions/csv/', views.export_contributions_csv, name='export_contributions_csv'),
    #path('', include('core.urls')),  # app URLs
    #path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('login/', custom_login_view, name='login'),
    path('officer_dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    # NEW: Notification URLs (R4 requirement)
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/unread-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    
    # NEW: Real-time loan status (R7 requirement)
    path('api/loan/<int:loan_id>/status/', views.check_loan_status, name='check_loan_status'),
    
    # NEW: Enhanced loan management
    path('admin/disburse_loan/<int:loan_id>/', views.disburse_loan, name='disburse_loan'),
    #path('officer/loan/<int:loan_id>/repayment/', views.add_loan_repayment, name='add_loan_repayment'),
    #path('customer/<str:customer_id>/', views.customer_detail, name='customer_detail'),
    path('submit-daily-total/', views.submit_daily_total, name='submit_daily_total'),
    path('officer/customer/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    # Keep admin at the end
    #path('admin/', admin.site.urls),
    path('admin/officers/', views.manage_officers, name='manage_officers'),
    path('admin/officers/add/', views.add_collection_officer, name='add_collection_officer'),
    path('admin/officers/edit/<int:officer_id>/', views.edit_collection_officer, name='edit_collection_officer'),
    path('admin/officers/delete/<int:officer_id>/', views.delete_collection_officer, name='delete_collection_officer'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

