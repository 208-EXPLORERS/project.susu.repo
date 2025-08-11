from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Community(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'core'
        verbose_name_plural = "Communities"


class CollectionOfficer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.community.name})"
    
    class Meta:
        app_label = 'core'


class Customer(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    is_active = models.BooleanField(default=True)
    officer = models.ForeignKey(
        'CollectionOfficer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers'
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=200)
    customer_id = models.CharField(max_length=10, unique=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    date_joined = models.DateField(auto_now_add=True)
    missed_days = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to='customer_photos/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Only auto-generate customer_id if it hasn't been set
        if not self.customer_id and self.officer:
            # Use first 2 letters of address, fallback to 'XX' if too short
            address_code = (self.address[:2].upper() if len(self.address) >= 2 else "XX")
            
            # Count existing customers under the same officer
            count = Customer.objects.filter(officer=self.officer).count() + 1
            
            number_code = str(count).zfill(3)
            self.customer_id = f"{address_code}{number_code}"

        super().save(*args, **kwargs)

    def total_savings(self):
        """Calculate total savings from all contributions"""
        return self.contributions.aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    def last_contribution_date(self):
        """Get the datetime of last contribution"""
        last_contribution = self.contributions.order_by('-date').first()
        return last_contribution.date if last_contribution else None

    def days_since_last_contribution(self):
        """Calculate days since last contribution"""
        last_datetime = self.last_contribution_date()
        if last_datetime:
           # Convert both to date objects for proper comparison
           return (timezone.now().date() - last_datetime.date()).days
        return None

    def update_status(self):
        """Update customer status based on missed contributions"""
        days_missed = self.days_since_last_contribution()
        if days_missed and days_missed > 7:  # 7 days threshold
            self.status = 'inactive'
            self.missed_days = days_missed
        else:
            self.status = 'active'
            self.missed_days = 0
        self.save()

    def __str__(self):
        return f"{self.name} ({self.customer_id})"
    
    class Meta:
        app_label = 'core'


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('contribution', 'Contribution'),
        ('withdrawal', 'Withdrawal'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('loan_repayment', 'Loan Repayment'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='contribution')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)  # Super admin approval
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.amount} on {self.date.date()}"
    
    class Meta:
        app_label = 'core'
        ordering = ['-date']


class DailySubmission(models.Model):
    officer = models.ForeignKey(CollectionOfficer, on_delete=models.CASCADE, related_name='submissions')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    submitted = models.BooleanField(default=True)
    approved = models.BooleanField(default=False)
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_submissions')

    class Meta:
        unique_together = ('officer', 'date')  # Prevent duplicate daily entries
        app_label = 'core'
        ordering = ['-date']

    def __str__(self):
        return f"{self.officer} - {self.total_amount} on {self.date}"


class Contribution(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # REMOVED: unique_together won't work properly with DateTimeField
        app_label = 'core'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.customer.name} - {self.amount} on {self.date}"
class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaid', 'Repaid'),
        ('defaulted', 'Defaulted'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length=200, help_text="Purpose of the loan")
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_loans')
    date_approved = models.DateTimeField(null=True, blank=True)
    date_disbursed = models.DateTimeField(null=True, blank=True)
    repayment_period_months = models.PositiveIntegerField(default=12, help_text="Repayment period in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Interest rate percentage")
    monthly_repayment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_repayment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_repaid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Calculate repayment amounts if loan is approved
        if self.status == 'approved' and not self.monthly_repayment:
            principal = float(self.amount)
            rate = float(self.interest_rate) / 100 / 12  # Monthly interest rate
            months = self.repayment_period_months
            
            if rate > 0:
                # Calculate monthly payment using loan formula
                monthly_payment = principal * (rate * (1 + rate)**months) / ((1 + rate)**months - 1)
            else:
                monthly_payment = principal / months
                
            self.monthly_repayment = round(monthly_payment, 2)
            self.total_repayment = round(monthly_payment * months, 2)
        
        super().save(*args, **kwargs)

    def remaining_balance(self):
        """Calculate remaining loan balance"""
        if self.total_repayment:
            return max(0, float(self.total_repayment) - float(self.amount_repaid))
        return 0

    def repayment_progress(self):
        """Calculate repayment progress percentage"""
        if self.total_repayment and self.total_repayment > 0:
            return min(100, (float(self.amount_repaid) / float(self.total_repayment)) * 100)
        return 0

    def is_overdue(self):
        """Check if loan repayment is overdue"""
        if self.status == 'disbursed' and self.date_disbursed:
            months_since_disbursed = (timezone.now().date() - self.date_disbursed.date()).days / 30
            return months_since_disbursed > self.repayment_period_months
        return False

    def __str__(self):
        return f"{self.customer.name} - {self.amount} ({self.status})"
    
    class Meta:
        app_label = 'core'
        ordering = ['-date_applied']


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update loan's amount_repaid
        self.loan.amount_repaid = self.loan.repayments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        # Update loan status if fully repaid
        if self.loan.amount_repaid >= self.loan.total_repayment:
            self.loan.status = 'repaid'
        
        self.loan.save()

    def __str__(self):
        return f"{self.loan.customer.name} - Repayment: {self.amount} on {self.date.date()}"
    
    class Meta:
        app_label = 'core'
        ordering = ['-date']


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('loan_application', 'Loan Application'),
        ('daily_submission', 'Daily Submission'),
        ('customer_inactive', 'Customer Inactive'),
        ('loan_overdue', 'Loan Overdue'),
        ('system_alert', 'System Alert'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)  # For linking to specific objects

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    class Meta:
        app_label = 'core'
        ordering = ['-created_at']