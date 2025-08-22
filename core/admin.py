from django.contrib import admin
from .models import Community, CollectionOfficer, Customer, Transaction, DailySubmission
from django.contrib.auth.models import User

# Community admin
@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name']

# Collection Officer admin
@admin.register(CollectionOfficer)
class CollectionOfficerAdmin(admin.ModelAdmin):
    list_display = ['user', 'community']
    search_fields = ['user__username', 'community__name']

# Customer admin
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_id', 'officer', 'is_active', 'missed_days', 'date_joined']
    list_filter = ['officer__community', 'is_active']
    search_fields = ['name',]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            officer = CollectionOfficer.objects.filter(user=request.user).first()
            if officer:
             obj.officer = officer
        super().save_model(request, obj, form, change)

# Transaction admin
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'date', 'approved']
    list_filter = ['date', 'approved']
    search_fields = ['customer__name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(customer__officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()

# Daily Submission admin
@admin.register(DailySubmission)
class DailySubmissionAdmin(admin.ModelAdmin):
    list_display = ['officer', 'date', 'total_amount', 'submitted', 'approved']
    list_filter = ['date', 'submitted', 'approved']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            officer = CollectionOfficer.objects.filter(user=request.user).first()
            if officer:
             obj.officer = officer
        super().save_model(request, obj, form, change)

