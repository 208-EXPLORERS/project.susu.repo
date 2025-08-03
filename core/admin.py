from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    CollectionOfficer, Customer, DailyContribution, 
    DailySubmission, Loan, SystemSettings
)


# Inline admin classes
class CollectionOfficerInline(admin.StackedInline):
    model = CollectionOfficer
    can_delete = False
    verbose_name_plural = 'Collection Officer Details'


class CustomerInline(admin.TabularInline):
    model = Customer
    extra = 0
    fields = ('customer_id', 'first_name', 'last_name', 'town', 'is_active')
    readonly_fields = ('customer_id',)


class DailyContributionInline(admin.TabularInline):
    model = DailyContribution
    extra = 0
    fields = ('date', 'amount', 'status', 'notes')
    readonly_fields = ('date', 'amount')


# Custom User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (CollectionOfficerInline,)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see their own user account
        return qs.filter(id=request.user.id)


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(CollectionOfficer)
class CollectionOfficerAdmin(admin.ModelAdmin):
    list_display = ('officer_id', 'get_full_name', 'phone_number', 'get_total_customers', 'is_active', 'date_joined')
    list_filter = ('is_active', 'date_joined')
    search_fields = ('officer_id', 'user__first_name', 'user__last_name', 'phone_number')
    readonly_fields = ('date_joined', 'get_total_customers', 'get_today_collections')
    inlines = [CustomerInline]
    
    fieldsets = (
        ('Officer Information', {
            'fields': ('user', 'officer_id', 'phone_number', 'address', 'is_active')
        }),
        ('Statistics', {
            'fields': ('get_total_customers', 'get_today_collections', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Full Name'
    
    def get_total_customers(self, obj):
        return obj.get_total_customers()
    get_total_customers.short_description = 'Active Customers'
    
    def get_today_collections(self, obj):
        return f"${obj.get_today_collections():.2f}"
    get_today_collections.short_description = 'Today\'s Collections'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see their own record
        return qs.filter(user=request.user)
    
    def has_add_permission(self, request):
        # Only superusers can add collection officers
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete collection officers
        return request.user.is_superuser


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'get_full_name', 'collection_officer', 'town', 'daily_contribution_amount', 'get_status_badge', 'last_contribution_date')
    list_filter = ('is_active', 'town', 'collection_officer', 'date_joined')
    search_fields = ('customer_id', 'first_name', 'last_name', 'phone_number', 'town')
    readonly_fields = ('customer_id', 'date_joined', 'get_total_contributions', 'get_contribution_streak', 'consecutive_missed_days')
    inlines = [DailyContributionInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('customer_id', 'first_name', 'last_name', 'phone_number', 'address', 'town', 'photo')
        }),
        ('Account Information', {
            'fields': ('collection_officer', 'daily_contribution_amount', 'is_active', 'last_contribution_date', 'consecutive_missed_days', 'max_missed_days')
        }),
        ('Statistics', {
            'fields': ('get_total_contributions', 'get_contribution_streak', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def get_status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        else:
            return format_html('<span style="color: red;">●</span> Inactive')
    get_status_badge.short_description = 'Status'
    
    def get_total_contributions(self, obj):
        return f"${obj.get_total_contributions():.2f}"
    get_total_contributions.short_description = 'Total Contributions'
    
    def get_contribution_streak(self, obj):
        return f"{obj.get_contribution_streak()} days"
    get_contribution_streak.short_description = 'Current Streak'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see their own customers
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(collection_officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "collection_officer":
            if not request.user.is_superuser:
                # Collection officers can only assign customers to themselves
                try:
                    officer = CollectionOfficer.objects.get(user=request.user)
                    kwargs["queryset"] = CollectionOfficer.objects.filter(id=officer.id)
                except CollectionOfficer.DoesNotExist:
                    kwargs["queryset"] = CollectionOfficer.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(DailyContribution)
class DailyContributionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'date', 'get_status_badge', 'time_recorded', 'approved_by')
    list_filter = ('status', 'date', 'customer__collection_officer')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__customer_id')
    readonly_fields = ('time_recorded', 'approved_by', 'approved_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Contribution Details', {
            'fields': ('customer', 'amount', 'date', 'notes')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'time_recorded')
        }),
    )
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        return format_html(
            '<span style="color: {};">●</span> {}',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see contributions from their customers
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(customer__collection_officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            if not request.user.is_superuser:
                # Collection officers can only add contributions for their customers
                try:
                    officer = CollectionOfficer.objects.get(user=request.user)
                    kwargs["queryset"] = Customer.objects.filter(collection_officer=officer)
                except CollectionOfficer.DoesNotExist:
                    kwargs["queryset"] = Customer.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if obj.status == 'approved' and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(DailySubmission)
class DailySubmissionAdmin(admin.ModelAdmin):
    list_display = ('collection_officer', 'date', 'total_amount_submitted', 'total_amount_calculated', 'get_variance', 'get_status_badge', 'submission_time')
    list_filter = ('status', 'date', 'collection_officer')
    search_fields = ('collection_officer__officer_id', 'collection_officer__user__first_name', 'collection_officer__user__last_name')
    readonly_fields = ('submission_time', 'total_amount_calculated', 'get_variance', 'reviewed_by', 'reviewed_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('collection_officer', 'date', 'total_amount_submitted', 'notes')
        }),
        ('Calculated Amounts', {
            'fields': ('total_amount_calculated', 'get_variance')
        }),
        ('Review & Approval', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'submission_time')
        }),
    )
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'flagged': 'red'
        }
        return format_html(
            '<span style="color: {};">●</span> {}',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_variance(self, obj):
        variance = obj.get_variance()
        color = 'red' if variance != 0 else 'green'
        return format_html('<span style="color: {};">${:.2f}</span>', color, variance)
    get_variance.short_description = 'Variance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see their own submissions
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(collection_officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "collection_officer":
            if not request.user.is_superuser:
                # Collection officers can only create submissions for themselves
                try:
                    officer = CollectionOfficer.objects.get(user=request.user)
                    kwargs["queryset"] = CollectionOfficer.objects.filter(id=officer.id)
                except CollectionOfficer.DoesNotExist:
                    kwargs["queryset"] = CollectionOfficer.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        # Calculate expected amount
        obj.calculate_expected_amount()
        
        # Auto-approve if amounts match
        if not change:  # Only for new submissions
            obj.auto_approve_if_matches()
        
        if obj.status in ['approved', 'flagged'] and not obj.reviewed_by:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        
        super().save_model(request, obj, form, change)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'amount', 'get_status_badge', 'request_date', 'approved_by', 'decision_date')
    list_filter = ('status', 'request_date', 'decision_date', 'requested_by')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__customer_id', 'purpose')
    readonly_fields = ('request_date', 'decision_date', 'approved_by')
    date_hierarchy = 'request_date'
    
    fieldsets = (
        ('Loan Request', {
            'fields': ('customer', 'requested_by', 'amount', 'purpose', 'request_date')
        }),
        ('Decision', {
            'fields': ('status', 'approved_by', 'decision_date', 'decision_notes')
        }),
        ('Repayment', {
            'fields': ('expected_repayment_date', 'actual_repayment_date', 'repayment_amount'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'rejected': 'red',
            'disbursed': 'green',
            'repaid': 'gray'
        }
        return format_html(
            '<span style="color: {};">●</span> {}',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Collection officers can only see loans for their customers
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return qs.filter(customer__collection_officer=officer)
        except CollectionOfficer.DoesNotExist:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            if not request.user.is_superuser:
                # Collection officers can only request loans for their customers
                try:
                    officer = CollectionOfficer.objects.get(user=request.user)
                    kwargs["queryset"] = Customer.objects.filter(collection_officer=officer)
                except CollectionOfficer.DoesNotExist:
                    kwargs["queryset"] = Customer.objects.none()
        elif db_field.name == "requested_by":
            if not request.user.is_superuser:
                # Auto-set to current officer
                try:
                    officer = CollectionOfficer.objects.get(user=request.user)
                    kwargs["queryset"] = CollectionOfficer.objects.filter(id=officer.id)
                except CollectionOfficer.DoesNotExist:
                    kwargs["queryset"] = CollectionOfficer.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if obj.status in ['approved', 'rejected'] and not obj.approved_by:
            obj.approved_by = request.user
            obj.decision_date = timezone.now()
        super().save_model(request, obj, form, change)
    
    def has_change_permission(self, request, obj=None):
        # Only superusers can approve/reject loans
        if obj and obj.status == 'pending':
            return request.user.is_superuser
        return super().has_change_permission(request, obj)


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at', 'updated_by')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_module_permission(self, request):
        # Only superusers can access system settings
        return request.user.is_superuser


# Customize admin site
admin.site.site_header = 'Susu System Administration'
admin.site.site_title = 'Susu System Admin'
admin.site.index_title = 'Welcome to Susu System Administration'
