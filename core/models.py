from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import datetime, timedelta
import string


class CollectionOfficer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    officer_id = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.officer_id})"
    
    def get_total_customers(self):
        return self.customers.filter(is_active=True).count()
    
    def get_today_collections(self):
        today = timezone.now().date()
        return DailyContribution.objects.filter(
            customer__collection_officer=self,
            date=today
        ).aggregate(total=models.Sum('amount'))['total'] or 0


class Customer(models.Model):
    customer_id = models.CharField(max_length=10, unique=True, blank=True)
    collection_officer = models.ForeignKey(CollectionOfficer, on_delete=models.CASCADE, related_name='customers')
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField()
    town = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='customer_photos/', blank=True, null=True)
    
    # Account Information
    daily_contribution_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_contribution_date = models.DateField(blank=True, null=True)
    consecutive_missed_days = models.IntegerField(default=0)
    
    # Settings
    max_missed_days = models.IntegerField(default=7)  # Auto-inactive after N days
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = self.generate_customer_id()
        super().save(*args, **kwargs)
    
    def generate_customer_id(self):
        # Get first two letters of town/address
        prefix = ''.join([c.upper() for c in self.town[:2] if c.isalpha()])
        if len(prefix) < 2:
            prefix = ''.join([c.upper() for c in self.address[:2] if c.isalpha()])
        if len(prefix) < 2:
            prefix = "CU"  # Default prefix
        
        # Get next available number for this officer
        existing_customers = Customer.objects.filter(
            collection_officer=self.collection_officer,
            customer_id__startswith=prefix
        ).count()
        
        number = str(existing_customers + 1).zfill(3)
        return f"{prefix}{number}"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.customer_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def check_and_update_status(self):
        """Check if customer should be marked inactive due to missed contributions"""
        today = timezone.now().date()
        if self.last_contribution_date:
            days_since_last = (today - self.last_contribution_date).days
            if days_since_last > self.max_missed_days:
                self.is_active = False
                self.consecutive_missed_days = days_since_last
                self.save()
    
    def get_total_contributions(self):
        return DailyContribution.objects.filter(
            customer=self, 
            status='approved'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_contribution_streak(self):
        """Get current contribution streak in days"""
        contributions = DailyContribution.objects.filter(
            customer=self,
            status='approved'
        ).order_by('-date')
        
        if not contributions.exists():
            return 0
        
        streak = 0
        expected_date = timezone.now().date()
        
        for contribution in contributions:
            if contribution.date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break
        
        return streak


class DailyContribution(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField()
    time_recorded = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    # Approval tracking
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_contributions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['customer', 'date']
        ordering = ['-date', '-time_recorded']
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.amount} on {self.date}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update customer's last contribution date if approved
        if self.status == 'approved':
            if not self.customer.last_contribution_date or self.date > self.customer.last_contribution_date:
                self.customer.last_contribution_date = self.date
                self.customer.consecutive_missed_days = 0
                self.customer.save()


class DailySubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('flagged', 'Flagged'),
    ]
    
    collection_officer = models.ForeignKey(CollectionOfficer, on_delete=models.CASCADE, related_name='submissions')
    date = models.DateField()
    total_amount_submitted = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_amount_calculated = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    submission_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    # Approval tracking
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['collection_officer', 'date']
        ordering = ['-date', '-submission_time']
    
    def __str__(self):
        return f"{self.collection_officer} - {self.total_amount_submitted} on {self.date}"
    
    def calculate_expected_amount(self):
        """Calculate expected amount based on daily contributions for this date"""
        total = DailyContribution.objects.filter(
            customer__collection_officer=self.collection_officer,
            date=self.date
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.total_amount_calculated = total
        return total
    
    def get_variance(self):
        """Get difference between submitted and calculated amounts"""
        return self.total_amount_submitted - self.total_amount_calculated
    
    def auto_approve_if_matches(self):
        """Auto-approve if submitted amount matches calculated amount"""
        if abs(self.get_variance()) < 0.01:  # Allow for small rounding differences
            self.status = 'approved'
            self.reviewed_at = timezone.now()
            self.save()
            return True
        return False


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaid', 'Fully Repaid'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    requested_by = models.ForeignKey(CollectionOfficer, on_delete=models.CASCADE, related_name='loan_requests')
    
    # Loan Details
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    purpose = models.TextField()
    request_date = models.DateTimeField(auto_now_add=True)
    
    # Approval Details
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_loans')
    decision_date = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    
    # Repayment Details
    expected_repayment_date = models.DateField(null=True, blank=True)
    actual_repayment_date = models.DateField(null=True, blank=True)
    repayment_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['-request_date']
    
    def __str__(self):
        return f"Loan #{self.id} - {self.customer.get_full_name()} - {self.amount}"
    
    def can_request_loan(self):
        """Check if customer is eligible for a loan"""
        # Basic eligibility: active customer with at least 30 days of contributions
        if not self.customer.is_active:
            return False, "Customer is not active"
        
        contribution_days = DailyContribution.objects.filter(
            customer=self.customer,
            status='approved'
        ).count()
        
        if contribution_days < 30:
            return False, f"Customer needs at least 30 days of contributions (has {contribution_days})"
        
        # Check for existing pending/active loans
        existing_loans = Loan.objects.filter(
            customer=self.customer,
            status__in=['pending', 'approved', 'disbursed']
        ).exists()
        
        if existing_loans:
            return False, "Customer has an existing active loan"
        
        return True, "Eligible for loan"


class SystemSettings(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
