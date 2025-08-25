from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import CollectionOfficer, Customer, Transaction, DailySubmission, Contribution, Loan, Notification, Community
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.views.generic.edit import CreateView
from .forms import CustomerForm, TransactionForm, ContributionForm, LoanForm,LoanRepaymentForm, CollectionOfficerForm
from django.urls import reverse_lazy 
from django.utils import timezone
from django.db.models import Q, Sum, Count
from .utils import render_to_pdf
import csv
from django.http import HttpResponse
from .decorators import officer_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django import forms
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from datetime import timedelta
from .utils import get_business_day





@method_decorator(login_required, name='dispatch')
class OfficerCustomerListView(ListView):
    model = Customer
    template_name = 'core/officer_customers.html'
    context_object_name = 'customers'

    def get_queryset(self):
        try:
            officer = CollectionOfficer.objects.get(user=self.request.user)
            return Customer.objects.filter(officer=officer)
        except CollectionOfficer.DoesNotExist:
            messages.error(self.request, "Officer profile not found.")
            return Customer.objects.none()
    

@method_decorator(login_required, name='dispatch')
class CustomerCreateView(CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/add_customer.html'
    success_url = '/officer/customers/'

    def form_valid(self, form):
        try:
            officer = CollectionOfficer.objects.get(user=self.request.user)
            form.instance.officer = officer
            return super().form_valid(form)
        except CollectionOfficer.DoesNotExist:
            messages.error(self.request, "Officer profile not found.")
            return redirect('login')
    

@method_decorator(login_required, name='dispatch')
class AddTransactionView(CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/add_transaction.html'
    success_url = reverse_lazy('officer_dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            officer = CollectionOfficer.objects.get(user=self.request.user)
            # Assuming Transaction.officer field expects CollectionOfficer instance
            form.instance.officer = officer
            return super().form_valid(form)
        except CollectionOfficer.DoesNotExist:
            messages.error(self.request, "Officer profile not found.")
            return redirect('login')

@login_required
def officer_customers(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('logout')

    customers = Customer.objects.filter(officer=officer)
    
    # Get filter parameters
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')

    # Apply search filter
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(customer_id__icontains=query) |
            Q(address__icontains=query)
        )

    # Apply status filter
    if status_filter and status_filter in ['active', 'inactive']:
        customers = customers.filter(status=status_filter)

    # Get approved daily submissions for this officer
    approved_submissions = DailySubmission.objects.filter(
        officer=officer, 
        approved=True
    )

    # Add contribution data for each customer before sorting
    customers_list = list(customers)
    for customer in customers_list:
        # Calculate total savings from approved submissions only
        customer.total_savings = 0
        
        for submission in approved_submissions:
            business_day_start = timezone.make_aware(
                timezone.datetime.combine(submission.date, timezone.datetime.min.time())
            ) + timedelta(hours=6)
            business_day_end = business_day_start + timedelta(hours=24)
            
            day_contributions = customer.contributions.filter(
                date__range=[business_day_start, business_day_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            customer.total_savings += day_contributions
        
        # Last contribution date (this can remain as is)
        last_contribution = customer.contributions.order_by('-date').first()
        customer.last_contribution_date = last_contribution.date if last_contribution else None

    # Apply sorting (rest remains the same)
    if sort_by == 'name':
        customers_list.sort(key=lambda x: x.name.lower())
    elif sort_by == '-name':
        customers_list.sort(key=lambda x: x.name.lower(), reverse=True)
    elif sort_by == 'total_savings':
        customers_list.sort(key=lambda x: x.total_savings or 0)
    elif sort_by == '-total_savings':
        customers_list.sort(key=lambda x: x.total_savings or 0, reverse=True)
    # ... rest of sorting logic

    # Rest of the view remains the same
    class CustomerList:
        def __init__(self, items):
            self.items = items
        
        def __iter__(self):
            return iter(self.items)
        
        def __len__(self):
            return len(self.items)
        
        @property
        def count(self):
            return len(self.items)
    
    customers = CustomerList(customers_list)
    
    context = {
        'customers': customers,
        'query': query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'officer': officer,
    }
    
    return render(request, 'core/officer_customers.html', context)

@officer_required
def add_customer(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data['name']
            address = form.cleaned_data['address']

            # Check if this customer already exists for this officer
            if Customer.objects.filter(name=name, address=address, officer=officer).exists():
                messages.error(request, "A customer with this name and address already exists.")
                return redirect('add_customer')

            # Save new customer and assign officer (only save once!)
            customer = form.save(commit=False)
            customer.officer = officer
            customer.save()  # Now customer_id will be properly generated

            messages.success(request, f"Customer '{customer.name}' added successfully.")
            return redirect('officer_customers')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = CustomerForm()

    return render(request, 'core/add_customer.html', {'form': form})

@officer_required
def add_transaction(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')

    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            # Assuming Transaction.officer field expects CollectionOfficer instance
            transaction.officer = officer
            transaction.save()
            messages.success(request, "Transaction added successfully.")
            return redirect('officer_customers')
    else:
        form = TransactionForm()
        form.fields['customer'].queryset = Customer.objects.filter(officer=officer)
    
    return render(request, 'core/add_transaction.html', {'form': form})


@officer_required
def customer_transactions(request, customer_id):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    transactions = customer.transactions.all().order_by('-date')
    contributions = customer.contributions.all().order_by('-date')
    
    return render(request, 'core/customer_transactions.html', {
        'customer': customer,
        'transactions': transactions,
        'contributions': contributions,
    })

@login_required
def submit_daily_total(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    # Use business day for consistency
    business_day = get_business_day()
    
    if DailySubmission.objects.filter(officer=officer, date=business_day).exists():
        return render(request, 'core/already_submitted.html', {'date': business_day})
    
    # Auto calculate total from today's contributions (6 AM - 6 AM cycle)
    officer_customers = Customer.objects.filter(officer=officer)
    
    business_day_start = timezone.make_aware(
        timezone.datetime.combine(business_day, timezone.datetime.min.time())
    ) + timedelta(hours=6)  # Start at 6 AM
    business_day_end = business_day_start + timedelta(hours=24)  # End at 6 AM next day
    
    contributions = Contribution.objects.filter(
        customer__in=officer_customers,
        date__range=[business_day_start, business_day_end]
    )
    auto_total = contributions.aggregate(total=Sum('amount'))['total'] or 0
    
    if request.method == 'POST':
        submission = DailySubmission.objects.create(
            officer=officer,
            total_amount=auto_total,
            date=business_day  # Use business day instead of today
        )
        messages.success(request, "Daily total submitted successfully.")
        return redirect('officer_dashboard')
    
    return render(request, 'core/submit_daily_total.html', {
        'auto_total': auto_total,
        'date': business_day,
        'contributions': contributions,
    })

@user_passes_test(lambda u: u.is_superuser)
def review_daily_submissions(request):
    # Show all unApproved submissions, not just today's
    submissions = DailySubmission.objects.filter(
        approved=False
    ).select_related('officer__user').order_by('-date', '-submitted_at')
    
    # Add some context for filtering
    context = {
        'submissions': submissions,
        'total_pending': submissions.count(),
    }
    
    return render(request, 'core/review_submissions.html', context)

@user_passes_test(lambda u: u.is_superuser)
def approve_submission(request, submission_id):
    submission = get_object_or_404(DailySubmission, id=submission_id)
    submission.approved = True
    submission.save()
    messages.success(request, f"Submission by {submission.officer} approved successfully.")
    return redirect('review_submissions')


@officer_required
def officer_dashboard(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    customers = Customer.objects.filter(officer=officer)

    # Get filter parameters
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')
    order = request.GET.get('order', 'asc')

    # Apply search and status filters (same as before)
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(customer_id__icontains=query) |
            Q(address__icontains=query)
        )

    if status_filter and status_filter in ['active', 'inactive']:
        customers = customers.filter(status=status_filter)

    # Apply sorting for database fields
    if sort_by in ['name', 'customer_id', 'date_joined'] and sort_by not in ['total_savings', 'last_contribution']:
        sort_field = sort_by
        if order == 'desc':
            sort_field = f'-{sort_field}'
        customers = customers.order_by(sort_field)
    else:
        customers = customers.order_by('name')

    total_customers = customers.count()

    # Today's collections calculation (same as before)
    business_day = get_business_day()
    business_day_start = timezone.make_aware(
        timezone.datetime.combine(business_day, timezone.datetime.min.time())
    ) + timedelta(hours=6)
    business_day_end = business_day_start + timedelta(hours=24)
    
    today_contributions = Contribution.objects.filter(
        customer__in=customers,
        date__range=[business_day_start, business_day_end]
    )
    total_today_collections = today_contributions.aggregate(
        total=Sum('amount')
    )['total'] or 0

    # Loan counts (same as before)
    pending_loans_count = Loan.objects.filter(
        customer__in=customers, 
        status='pending'
    ).count()

    approved_loans_count = Loan.objects.filter(
        customer__in=customers, 
        status='approved'
    ).count()

    # Get approved daily submissions for this officer
    approved_submissions = DailySubmission.objects.filter(
        officer=officer, 
        approved=True
    )

    # Add savings data to customers for display
    customers_list = list(customers)
    for customer in customers_list:
        # Calculate total savings from approved submissions only
        customer.total_savings = 0
        
        for submission in approved_submissions:
            business_day_start = timezone.make_aware(
                timezone.datetime.combine(submission.date, timezone.datetime.min.time())
            ) + timedelta(hours=6)
            business_day_end = business_day_start + timedelta(hours=24)
            
            day_contributions = customer.contributions.filter(
                date__range=[business_day_start, business_day_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            customer.total_savings += day_contributions
        
        last_contribution = customer.contributions.order_by('-date').first()
        customer.last_contribution_date = last_contribution.date if last_contribution else None

    # Handle sorting for calculated fields
    if sort_by == 'total_savings':
        customers_list.sort(
            key=lambda x: x.total_savings or 0, 
            reverse=(order == 'desc')
        )
    elif sort_by == 'last_contribution':
        customers_list.sort(
            key=lambda x: x.last_contribution_date or timezone.now().date() - timedelta(days=9999), 
            reverse=(order == 'desc')
        )

    context = {
        'officer': officer,
        'customers': customers_list,
        'total_customers': total_customers,
        'total_today_collections': total_today_collections,
        'pending_loans': pending_loans_count,
        'approved_loans': approved_loans_count,
        'query': query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'order': order,
        'recent_notifications': getattr(request.user, 'notifications', None).order_by('-created_at')[:5] if hasattr(request.user, 'notifications') else [],
        'unread_notifications': getattr(request.user, 'notifications', None).filter(is_read=False).count() if hasattr(request.user, 'notifications') else 0,
    }
    return render(request, 'core/officer_dashboard.html', context)

@officer_required
def add_contribution(request, customer_id):
    officer = request.user.collectionofficer
    customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    
    # Use business day instead of calendar day
    business_day = get_business_day()
    
    # Check contributions for this business day (6 AM to 6 AM cycle)
    business_day_start = timezone.make_aware(
        timezone.datetime.combine(business_day, timezone.datetime.min.time())
    ) + timedelta(hours=6)  # Start at 6 AM
    
    business_day_end = business_day_start + timedelta(hours=24)  # End at 6 AM next day
    
    if Contribution.objects.filter(
        customer=customer, 
        date__range=[business_day_start, business_day_end]
    ).exists():
        messages.warning(request, f"{customer.name} has already contributed today (business day).")
        return redirect('officer_customers')
    
    if request.method == 'POST':
        form = ContributionForm(request.POST, customer=customer)
        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.customer = customer
            contribution.recorded_by = request.user
            contribution.save()
            
            messages.success(request, f"Recorded GHS {contribution.amount} for {customer.name}.")
            return redirect('officer_dashboard')
    else:
        form = ContributionForm(customer=customer)
    
    return render(request, 'core/add_contribution.html', {
        'form': form,
        'customer': customer
    })

@login_required
def apply_loan(request, customer_id):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')

    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.customer = customer
            loan.save()
            messages.success(request, f"Loan application of GHS {loan.amount} submitted for {customer.name}.")
            return redirect('officer_dashboard')
    else:
        form = LoanForm()

    return render(request, 'core/apply_loan.html', {'form': form, 'customer': customer})


@user_passes_test(lambda u: u.is_superuser)
def review_loans(request):
    loans = Loan.objects.filter(status='pending').select_related('customer__officer__user')
    return render(request, 'core/review_loans.html', {'loans': loans})


@user_passes_test(lambda u: u.is_superuser)
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = 'approved'
    loan.date_approved = timezone.now()
    loan.approved_by = request.user
    loan.save()
    messages.success(request, f"Loan of GHS {loan.amount} for {loan.customer.name} approved successfully.")
    return redirect('review_loans')


@user_passes_test(lambda u: u.is_superuser)
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = 'rejected'
    loan.save()
    messages.success(request, f"Loan of GHS {loan.amount} for {loan.customer.name} rejected.")
    return redirect('review_loans')

@user_passes_test(lambda u: u.is_superuser)
def export_contributions_pdf(request):
    # Group contributions by customer
    customers = Customer.objects.all().select_related('officer__user')
    customer_data = []

    grand_total = 0

    for customer in customers:
        contributions = customer.contributions.order_by('-date')[:5]
        total = customer.contributions.aggregate(total=Sum('amount'))['total'] or 0
        grand_total += total

        # FIX: Handle cases where customer.officer is None
        if customer.officer and customer.officer.user:
            officer_name = customer.officer.user.get_full_name() or customer.officer.user.username
        else:
            officer_name = "No Officer Assigned"

        customer_data.append({
            'name': customer.name,
            'customer_id': customer.customer_id,
            'address': customer.address,
            'officer': officer_name,
            'total': total,
            'recent_contributions': contributions,
        })

    context = {
        'customer_data': customer_data,
        'grand_total': grand_total,
        'export_date': timezone.now().date(),
    }
    return render_to_pdf('core/pdf_contributions.html', context)

@user_passes_test(lambda u: u.is_superuser)
def export_contributions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contributions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Customer', 'Customer ID', 'Amount', 'Date', 'Recorded By', 'Officer'])

    contributions = Contribution.objects.select_related(
        'customer__officer__user', 'recorded_by'
    ).all().order_by('-date')

    for c in contributions:
        writer.writerow([
            c.customer.name, 
            c.customer.customer_id,
            c.amount, 
            c.date, 
            c.recorded_by.get_full_name() if c.recorded_by else 'N/A',
            c.customer.officer.user.get_full_name() if c.customer.officer else 'N/A'
        ])

    return response


@officer_required
def submission_history(request):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    submissions = DailySubmission.objects.filter(officer=officer).order_by('-date')

    return render(request, 'core/submission_history.html', {
        'submissions': submissions,
        'officer': officer,
    })


class CustomLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


def custom_login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                # ALWAYS redirect superusers/staff to YOUR custom admin dashboard
                if user.is_superuser or user.is_staff:
                    messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                    return redirect('dashboard')  # Use URL name instead of hardcoded path
                else:
                    try:
                        officer = CollectionOfficer.objects.get(user=user)
                        messages.success(request, f"Welcome back, {officer}!")
                        return redirect('officer_dashboard')
                    except CollectionOfficer.DoesNotExist:
                        messages.error(request, "No officer profile found for this user. Please contact administrator.")
                        return redirect('login')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = CustomLoginForm()

    return render(request, 'core/login.html', {'form': form})

# Additional utility view for customer details
@officer_required
def customer_detail(request, customer_id):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    contributions = customer.contributions.all().order_by('-date')
    
    # Calculate total savings from approved submissions only
    total_savings = 0
    approved_submissions = DailySubmission.objects.filter(
        officer=officer, 
        approved=True
    )
    
    for submission in approved_submissions:
        business_day_start = timezone.make_aware(
            timezone.datetime.combine(submission.date, timezone.datetime.min.time())
        ) + timedelta(hours=6)
        business_day_end = business_day_start + timedelta(hours=24)
        
        day_contributions = customer.contributions.filter(
            date__range=[business_day_start, business_day_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_savings += day_contributions
    
    loans = customer.loans.all().order_by('-date_applied')
    
    return render(request, 'core/customer_detail.html', {
        'customer': customer,
        'contributions': contributions,
        'total_savings': total_savings,
        'loans': loans,
    })

# Edit customer view
@officer_required
def edit_customer(request, customer_id):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer '{customer.name}' updated successfully.")
            return redirect('officer_customers')
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'core/edit_customer.html', {
        'form': form, 
        'customer': customer
    })

def create_notification(recipient, notification_type, title, message, related_object_id=None):
    """Helper function to create notifications"""
    Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_id=related_object_id
    )

# ENHANCED: Update your existing apply_loan view to add notifications
@login_required
def apply_loan(request, customer_id):
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        customer = get_object_or_404(Customer, id=customer_id, officer=officer)
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')

    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.customer = customer
            loan.save()
            
            # R4: Create notification for super admin
            from django.contrib.auth.models import User
            super_admins = User.objects.filter(is_superuser=True)
            for admin in super_admins:
                create_notification(
                    recipient=admin,
                    notification_type='loan_application',
                    title=f'New Loan Application - {customer.name}',
                    message=f'New loan application of GHS {loan.amount} submitted by {officer.user.get_full_name() or officer.user.username} for customer {customer.name} ({customer.customer_id}). Purpose: {loan.purpose}',
                    related_object_id=loan.id
                )
            
            messages.success(request, f"Loan application of GHS {loan.amount} submitted for {customer.name}.")
            return redirect('officer_dashboard')
    else:
        form = LoanForm()

    return render(request, 'core/apply_loan.html', {'form': form, 'customer': customer})

 #NEW: Real-time loan status check (R7 requirement)
@login_required
def check_loan_status(request, loan_id):
    """AJAX endpoint to check loan status in real-time"""
    try:
        if request.user.is_superuser:
            loan = get_object_or_404(Loan, id=loan_id)
        else:
            # Officers can only check their customers' loans
            officer = CollectionOfficer.objects.get(user=request.user)
            loan = get_object_or_404(Loan, id=loan_id, customer__officer=officer)
        
        return JsonResponse({
            'status': loan.status,
            'status_display': loan.get_status_display(),
            'date_approved': loan.date_approved.strftime('%Y-%m-%d %H:%M') if loan.date_approved else None,
            'approved_by': loan.approved_by.get_full_name() if loan.approved_by else None,
            'rejection_reason': loan.rejection_reason,
            'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except CollectionOfficer.DoesNotExist:
        return JsonResponse({'error': 'Officer profile not found'}, status=404)
    except Loan.DoesNotExist:
        return JsonResponse({'error': 'Loan not found'}, status=404)

# ENHANCED: Update your existing approve_loan view with better notifications
@user_passes_test(lambda u: u.is_superuser)
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = 'approved'
    loan.date_approved = timezone.now()
    loan.approved_by = request.user
    loan.save()
    
    # Notify the collection officer
    create_notification(
        recipient=loan.customer.officer.user,
        notification_type='loan_application',
        title=f'Loan Approved - {loan.customer.name}',
        message=f'Loan application of GHS {loan.amount} for {loan.customer.name} has been approved. Monthly repayment: GHS {loan.monthly_repayment}',
        related_object_id=loan.id
    )
    
    messages.success(request, f"Loan of GHS {loan.amount} for {loan.customer.name} approved successfully.")
    return redirect('review_loans')

# ENHANCED: Update your existing reject_loan view with better notifications
@user_passes_test(lambda u: u.is_superuser)
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        loan.status = 'rejected'
        loan.rejection_reason = rejection_reason
        loan.save()
        
        # Notify the collection officer
        create_notification(
            recipient=loan.customer.officer.user,
            notification_type='loan_application',
            title=f'Loan Rejected - {loan.customer.name}',
            message=f'Loan application of GHS {loan.amount} for {loan.customer.name} has been rejected. Reason: {rejection_reason}',
            related_object_id=loan.id
        )
        
        messages.success(request, f"Loan of GHS {loan.amount} for {loan.customer.name} rejected.")
        return redirect('review_loans')
    
    return render(request, 'core/reject_loan_confirm.html', {'loan': loan})

# NEW: Notifications management views
@login_required
def notifications_list(request):
    """View user's notifications"""
    notifications = request.user.notifications.order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('notifications_list')

@login_required
def get_unread_notifications_count(request):
    """AJAX endpoint to get unread notifications count"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


# NEW: Enhanced dashboard with notifications
@login_required
def dashboard(request):
    user = request.user

    # Route collection officers to their specific dashboard
    if hasattr(user, 'collectionofficer'):
        return redirect('officer_dashboard')

    if user.is_superuser:
        # Super admin dashboard
        total_officers = CollectionOfficer.objects.count()
        total_customers = Customer.objects.count()
        total_transactions = Transaction.objects.count()
        total_submissions = DailySubmission.objects.count()
        pending_loans = Loan.objects.filter(status='pending').count()
        
        # Calculate total savings from approved daily submissions only
        total_savings = 0
        approved_submissions = DailySubmission.objects.filter(approved=True)
        
        for submission in approved_submissions:
            # Get all customers under this officer
            officer_customers = Customer.objects.filter(officer=submission.officer)
            
            # Use business day logic (6 AM - 6 AM cycle) for the submission date
            business_day_start = timezone.make_aware(
                timezone.datetime.combine(submission.date, timezone.datetime.min.time())
            ) + timedelta(hours=6)  # Start at 6 AM
            business_day_end = business_day_start + timedelta(hours=24)  # End at 6 AM next day
            
            # Get all contributions for this officer's customers on this business day
            day_contributions = Contribution.objects.filter(
                customer__in=officer_customers,
                date__range=[business_day_start, business_day_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_savings += day_contributions
        
        # Recent notifications
        recent_notifications = user.notifications.order_by('-created_at')[:5]
        unread_notifications = user.notifications.filter(is_read=False).count()

        context = {
            'user': user,
            'role': 'Super Admin',
            'total_officers': total_officers,
            'total_customers': total_customers,
            'total_transactions': total_transactions,
            'total_submissions': total_submissions,
            'pending_loans': pending_loans,
            'total_savings': total_savings,
            'recent_notifications': recent_notifications,
            'unread_notifications': unread_notifications,
        }
        return render(request, 'core/super_dashboard.html', context)
    
    # Handle users who are not superusers or collection officers
    else:
        messages.error(request, 'Access denied. Your user role is not recognized.')
        return render(request, 'core/error.html', {
            'message': 'Access denied. Please contact the administrator.',
            'error_type': 'Permission Denied'
        })
    
# NEW: Loan disbursement management
@user_passes_test(lambda u: u.is_superuser)
def disburse_loan(request, loan_id):
    """Mark loan as disbursed"""
    loan = get_object_or_404(Loan, id=loan_id, status='approved')
    loan.status = 'disbursed'
    loan.date_disbursed = timezone.now()
    loan.save()
    
    # Create disbursement transaction
    Transaction.objects.create(
        customer=loan.customer,
        transaction_type='loan_disbursement',
        amount=loan.amount,
        remarks=f'Loan disbursement - {loan.purpose}',
        approved=True,
        processed_by=request.user
    )
    
    # Notify officer
    create_notification(
        recipient=loan.customer.officer.user,
        notification_type='loan_application',
        title=f'Loan Disbursed - {loan.customer.name}',
        message=f'Loan of GHS {loan.amount} for {loan.customer.name} has been disbursed.',
        related_object_id=loan.id
    )
    
    messages.success(request, f"Loan of GHS {loan.amount} disbursed to {loan.customer.name}.")
    return redirect('review_loans')

# NEW: Loan repayment view
@officer_required
def add_loan_repayment(request, loan_id):
    """Record loan repayment"""
    try:
        officer = CollectionOfficer.objects.get(user=request.user)
        loan = get_object_or_404(Loan, id=loan_id, customer__officer=officer, status='disbursed')
    except CollectionOfficer.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('login')
    
    if request.method == 'POST':
        form = LoanRepaymentForm(request.POST, loan=loan)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.loan = loan
            repayment.recorded_by = request.user
            repayment.save()
            
            messages.success(request, f"Repayment of GHS {repayment.amount} recorded for {loan.customer.name}.")
            return redirect('customer_detail', customer_id=loan.customer.id)
    else:
        form = LoanRepaymentForm(loan=loan)
    
    return render(request, 'core/add_loan_repayment.html', {
        'form': form,
        'loan': loan,
        'customer': loan.customer
    })

@user_passes_test(lambda u: u.is_superuser)
def add_collection_officer(request):
    if request.method == 'POST':
        form = CollectionOfficerForm(request.POST)
        if form.is_valid():
            officer = form.save()
            messages.success(request, f"Collection Officer '{officer.user.get_full_name()}' added successfully.")
            return redirect('manage_officers')
    else:
        form = CollectionOfficerForm()
    
    return render(request, 'core/add_collection_officer.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def manage_officers(request):
    officers = CollectionOfficer.objects.all().select_related('user', 'community').order_by('-created_at')
    
    # Add statistics for each officer
    for officer in officers:
        officer.customer_count = Customer.objects.filter(officer=officer).count()
        officer.total_collections = 0
        
        # Calculate total from approved submissions
        approved_submissions = DailySubmission.objects.filter(
            officer=officer, 
            approved=True
        )
        
        for submission in approved_submissions:
            officer_customers = Customer.objects.filter(officer=officer)
            business_day_start = timezone.make_aware(
                timezone.datetime.combine(submission.date, timezone.datetime.min.time())
            ) + timedelta(hours=6)
            business_day_end = business_day_start + timedelta(hours=24)
            
            day_contributions = Contribution.objects.filter(
                customer__in=officer_customers,
                date__range=[business_day_start, business_day_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            officer.total_collections += day_contributions
    
    return render(request, 'core/manage_officers.html', {'officers': officers})

@user_passes_test(lambda u: u.is_superuser)
def edit_collection_officer(request, officer_id):
    officer = get_object_or_404(CollectionOfficer, id=officer_id)
    
    if request.method == 'POST':
        # Update user information
        user = officer.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        
        # Update password if provided
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password:
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                communities = Community.objects.all()
                return render(request, 'core/edit_collection_officer.html', {
                    'officer': officer,
                    'communities': communities
                })
            
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                communities = Community.objects.all()
                return render(request, 'core/edit_collection_officer.html', {
                    'officer': officer,
                    'communities': communities
                })
            
            user.set_password(new_password)
        
        user.save()
        
        # Update officer information
        community_id = request.POST.get('community')
        if community_id:
            try:
                officer.community = Community.objects.get(id=community_id)
                officer.save()
            except Community.DoesNotExist:
                messages.error(request, "Invalid community selected.")
                communities = Community.objects.all()
                return render(request, 'core/edit_collection_officer.html', {
                    'officer': officer,
                    'communities': communities
                })
        
        messages.success(request, f"Officer '{user.get_full_name()}' updated successfully.")
        return redirect('manage_officers')
    
    communities = Community.objects.all()
    return render(request, 'core/edit_collection_officer.html', {
        'officer': officer,
        'communities': communities
    })

@user_passes_test(lambda u: u.is_superuser)
def delete_collection_officer(request, officer_id):
    officer = get_object_or_404(CollectionOfficer, id=officer_id)
    
    if request.method == 'POST':
        officer_name = officer.user.get_full_name()
        officer.user.delete()  # This will cascade delete the officer too
        messages.success(request, f"Officer '{officer_name}' deleted successfully.")
        return redirect('manage_officers')
    
    return render(request, 'core/delete_officer_confirm.html', {'officer': officer})


def home_view(request):
    """
    Root URL handler - redirects based on authentication and user type
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # User is authenticated, redirect based on user type
    if request.user.is_superuser or request.user.is_staff:
        return redirect('dashboard')  # Admin dashboard
    else:
        try:
            officer = CollectionOfficer.objects.get(user=request.user)
            return redirect('officer_dashboard')  # Officer dashboard
        except CollectionOfficer.DoesNotExist:
            messages.error(request, "No officer profile found for this user. Please contact administrator.")
            return redirect('login')



@login_required
def add_community(request):
    """View to add a new community - only for admin/staff"""
    if request.method == 'POST':
        community_name = request.POST.get('name', '').strip()
        
        if not community_name:
            messages.error(request, 'Community name is required.')
            return render(request, 'admin/add_community.html')
        
        # Check if community already exists
        if Community.objects.filter(name__iexact=community_name).exists():
            messages.error(request, f'Community "{community_name}" already exists.')
            return render(request, 'admin/add_community.html', {'name': community_name})
        
        try:
            # Create the community
            community = Community.objects.create(name=community_name)
            messages.success(request, f'Community "{community_name}" has been created successfully!')
            
            # Redirect to community list or back to form
            if 'save_and_continue' in request.POST:
                return redirect('add_community')  # Stay on the form to add more
            else:
                return redirect('community_list')  # Go to community list
                
        except Exception as e:
            messages.error(request, f'Error creating community: {str(e)}')
    
    return render(request, 'core/add_community.html')

@login_required
def community_list(request):
    """View to list all communities with statistics"""
    communities = Community.objects.annotate(
        officer_count=Count('collectionofficer'),
        customer_count=Count('collectionofficer__customers')
    ).order_by('name')
    
    context = {
        'communities': communities,
        'total_communities': communities.count(),
        'total_officers': CollectionOfficer.objects.count(),
        'total_customers': Customer.objects.count(),
    }
    
    return render(request, 'core/community_list.html', context)
