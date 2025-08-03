from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Customer, CollectionOfficer, DailyContribution, 
    DailySubmission, Loan
)


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers"""
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'phone_number', 
            'address', 'town', 'daily_contribution_amount', 
            'photo', 'max_missed_days'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter full address'
            }),
            'town': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter town/city'
            }),
            'daily_contribution_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'max_missed_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '7'
            })
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'phone_number': 'Phone Number',
            'address': 'Address',
            'town': 'Town/City',
            'daily_contribution_amount': 'Daily Contribution Amount ($)',
            'photo': 'Customer Photo',
            'max_missed_days': 'Max Missed Days (Auto-inactive)'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set collection officer if user is provided
        if user and hasattr(user, 'collectionofficer'):
            self.instance.collection_officer = user.collectionofficer

    def clean_daily_contribution_amount(self):
        amount = self.cleaned_data['daily_contribution_amount']
        if amount <= 0:
            raise forms.ValidationError("Daily contribution amount must be greater than 0")
        return amount

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise forms.ValidationError("Please enter a valid phone number")
        return phone


class DailyContributionForm(forms.ModelForm):
    """Form for recording daily contributions"""
    class Meta:
        model = DailyContribution
        fields = ['customer', 'amount', 'date', 'notes']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes...'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter customers by collection officer
        if user and hasattr(user, 'collectionofficer'):
            self.fields['customer'].queryset = Customer.objects.filter(
                collection_officer=user.collectionofficer,
                is_active=True
            ).order_by('customer_id')
        else:
            self.fields['customer'].queryset = Customer.objects.none()
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        date = cleaned_data.get('date')
        amount = cleaned_data.get('amount')

        if customer and date:
            # Check if contribution already exists for this customer and date
            existing = DailyContribution.objects.filter(
                customer=customer, 
                date=date
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise forms.ValidationError(
                    f"A contribution for {customer.get_full_name()} on {date} already exists."
                )

        if amount and amount <= 0:
            raise forms.ValidationError("Contribution amount must be greater than 0")

        return cleaned_data


class DailySubmissionForm(forms.ModelForm):
    """Form for daily cash submission by collection officers"""
    class Meta:
        model = DailySubmission
        fields = ['date', 'total_amount_submitted', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'total_amount_submitted': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about the submission...'
            })
        }
        labels = {
            'date': 'Submission Date',
            'total_amount_submitted': 'Total Amount Submitted ($)',
            'notes': 'Notes'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set collection officer
        if user and hasattr(user, 'collectionofficer'):
            self.instance.collection_officer = user.collectionofficer
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        officer = getattr(self.instance, 'collection_officer', None)

        if officer and date:
            # Check if submission already exists for this officer and date
            existing = DailySubmission.objects.filter(
                collection_officer=officer,
                date=date
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise forms.ValidationError(
                    f"A submission for {date} already exists."
                )

        return cleaned_data


class LoanForm(forms.ModelForm):
    """Form for loan requests"""
    class Meta:
        model = Loan
        fields = ['customer', 'amount', 'purpose', 'expected_repayment_date']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the purpose of this loan...'
            }),
            'expected_repayment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        labels = {
            'customer': 'Customer',
            'amount': 'Loan Amount ($)',
            'purpose': 'Purpose of Loan',
            'expected_repayment_date': 'Expected Repayment Date'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter customers by collection officer and only show eligible customers
        if user and hasattr(user, 'collectionofficer'):
            eligible_customers = []
            customers = Customer.objects.filter(
                collection_officer=user.collectionofficer,
                is_active=True
            )
            
            for customer in customers:
                eligible, reason = customer.loans.model().can_request_loan(customer)
                if eligible:
                    eligible_customers.append(customer.id)
            
            self.fields['customer'].queryset = Customer.objects.filter(
                id__in=eligible_customers
            ).order_by('customer_id')
            
            # Set the requesting officer
            self.instance.requested_by = user.collectionofficer
        else:
            self.fields['customer'].queryset = Customer.objects.none()

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Loan amount must be greater than 0")
        return amount

    def clean_customer(self):
        customer = self.cleaned_data['customer']
        if customer:
            # Double-check eligibility
            eligible, reason = customer.loans.model().can_request_loan(customer)
            if not eligible:
                raise forms.ValidationError(f"Customer is not eligible for a loan: {reason}")
        return customer


class LoanApprovalForm(forms.ModelForm):
    """Form for loan approval/rejection by super admin"""
    class Meta:
        model = Loan
        fields = ['status', 'decision_notes', 'expected_repayment_date', 'repayment_amount']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'decision_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes about the decision...'
            }),
            'expected_repayment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'repayment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit status choices to approval/rejection
        self.fields['status'].choices = [
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        repayment_amount = cleaned_data.get('repayment_amount')
        expected_date = cleaned_data.get('expected_repayment_date')

        if status == 'approved':
            if not expected_date:
                raise forms.ValidationError("Expected repayment date is required for approved loans")
            if not repayment_amount:
                # Default to loan amount if not specified
                cleaned_data['repayment_amount'] = self.instance.amount

        return cleaned_data


class CustomerSearchForm(forms.Form):
    """Form for searching and filtering customers"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, ID, or phone...'
        })
    )
    
    town = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by town...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Customers'),
            ('active', 'Active Only'),
            ('inactive', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )


class ContributionSearchForm(forms.Form):
    """Form for searching and filtering contributions"""
    customer = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by customer name or ID...'
        })
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
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Contributions'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )