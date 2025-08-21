from django import forms
from django.core.exceptions import ValidationError
from core.models import Customer, Transaction, DailySubmission, Contribution, Loan, CollectionOfficer, LoanRepayment, Community
from django.utils import timezone
from .utils import get_business_day
from datetime import timedelta
from django.contrib.auth.models import User

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'address', 'phone', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter customer full name',
                'required': True
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter customer address/location',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number (optional)',
                'pattern': '[0-9+\-\s()]*'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control-file'}),
        }
        labels = {
            'name': 'Full Name',
            'address': 'Address/Location',
            'phone': 'Phone Number',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip().title()
            if len(name) < 2:
                raise ValidationError("Name must be at least 2 characters long.")
        return name

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if address:
            address = address.strip().title()
            if len(address) < 2:
                raise ValidationError("Address must be at least 2 characters long.")
        return address

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and validate basic phone format
            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if phone and not phone.replace('+', '').isdigit():
                raise ValidationError("Please enter a valid phone number.")
        return phone


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['customer', 'transaction_type', 'amount', 'remarks']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter amount',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional remarks...'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TransactionForm, self).__init__(*args, **kwargs)
        
        if user:
            try:
                officer = CollectionOfficer.objects.get(user=user)
                self.fields['customer'].queryset = Customer.objects.filter(officer=officer)
            except CollectionOfficer.DoesNotExist:
                self.fields['customer'].queryset = Customer.objects.none()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount


class DailySubmissionForm(forms.ModelForm):
    class Meta:
        model = DailySubmission
        fields = ['total_amount', 'feedback']
        widgets = {
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Total amount collected today',
                'readonly': True  # Auto-calculated
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes for today...'
            }),
        }


from django.utils import timezone

class ContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = ['amount', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter contribution amount',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)  # Pass customer from view
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Contribution amount must be greater than zero.")
        if amount and amount > 10000:
            raise ValidationError("Contribution amount seems too high. Please verify.")
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        if self.customer:
            business_day = get_business_day()
            business_day_start = timezone.make_aware(
                timezone.datetime.combine(business_day, timezone.datetime.min.time())
            ) + timedelta(hours=6)
            business_day_end = business_day_start + timedelta(hours=24)
            
            if Contribution.objects.filter(
                customer=self.customer, 
                date__range=[business_day_start, business_day_end]
            ).exists():
                raise ValidationError(f"{self.customer.name} has already contributed today (business day).")
        return cleaned_data
    

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['amount', 'purpose', 'repayment_period_months', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1.00',
                'placeholder': 'Enter loan amount',
                'required': True
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What is this loan for? (e.g., Business, Emergency, etc.)',
                'required': True,
                'maxlength': 200
            }),
            'repayment_period_months': forms.Select(
                choices=[(i, f'{i} months') for i in [3, 6, 9, 12, 18, 24]],
                attrs={
                    'class': 'form-control',
                    'required': True
                }
            ),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional information or officer notes...'
            }),
        }
        labels = {
            'amount': 'Loan Amount (GHS)',
            'purpose': 'Purpose of Loan',
            'repayment_period_months': 'Repayment Period',
            'notes': 'Additional Notes',
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Loan amount must be greater than zero.")
        if amount and amount > 50000:  # Set reasonable limit
            raise ValidationError("Loan amount exceeds maximum limit of GHS 50,000.")
        return amount

    def clean_purpose(self):
        purpose = self.cleaned_data.get('purpose')
        if purpose:
            purpose = purpose.strip()
            if len(purpose) < 5:
                raise ValidationError("Please provide a more detailed purpose (at least 5 characters).")
        return purpose


class LoanApprovalForm(forms.ModelForm):
    """Form for super admin to approve/reject loans"""
    DECISION_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ]
    
    decision = forms.ChoiceField(choices=DECISION_CHOICES, widget=forms.RadioSelect)
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Reason for approval/rejection...'
        }),
        required=True,
        label='Decision Notes'
    )

    class Meta:
        model = Loan
        fields = ['decision', 'admin_notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-populate with existing data if editing
            if self.instance.status == 'approved':
                self.fields['decision'].initial = 'approved'
            elif self.instance.status == 'rejected':
                self.fields['decision'].initial = 'rejected'

    def save(self, commit=True, user=None):
        loan = super().save(commit=False)
        decision = self.cleaned_data['decision']
        admin_notes = self.cleaned_data['admin_notes']
        
        loan.status = decision
        loan.approved_by = user
        loan.date_approved = timezone.now()
        
        if decision == 'rejected':
            loan.rejection_reason = admin_notes
        else:
            loan.notes = admin_notes
            
        if commit:
            loan.save()
        return loan


class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanRepayment
        fields = ['amount', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter repayment amount',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Payment method, receipt number, etc...'
            }),
        }
        labels = {
            'amount': 'Repayment Amount (GHS)',
            'notes': 'Payment Notes',
        }

    def __init__(self, *args, **kwargs):
        self.loan = kwargs.pop('loan', None)
        super().__init__(*args, **kwargs)
        
        if self.loan:
            remaining = self.loan.remaining_balance()
            self.fields['amount'].widget.attrs['max'] = remaining
            self.fields['amount'].help_text = f'Remaining balance: GHS {remaining:.2f}'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Repayment amount must be greater than zero.")
            
        if self.loan:
            remaining = self.loan.remaining_balance()
            if amount > remaining:
                raise ValidationError(f"Repayment amount cannot exceed remaining balance of GHS {remaining:.2f}")
        
        return amount


class CustomerSearchForm(forms.Form):
    """Form for searching and filtering customers"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, or customer ID...',
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Customer.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class DateRangeForm(forms.Form):
    """Form for date range filtering in reports"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        initial=timezone.now().date().replace(day=1)  # First day of current month
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        initial=timezone.now().date()
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data
    
class CollectionOfficerForm(forms.ModelForm):
    # User fields
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)
    
    class Meta:
        model = CollectionOfficer
        fields = ['community']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match.")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Create the user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Create the collection officer
        officer = super().save(commit=False)
        officer.user = user
        
        if commit:
            officer.save()
        
        return officer