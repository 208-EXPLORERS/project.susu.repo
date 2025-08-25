#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'susu.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

# In Django shell or a management command
from core.models import Customer

# Find customers with empty customer_id
empty_customers = Customer.objects.filter(customer_id__in=['', None])

# Delete them or fix them
for customer in empty_customers:
    if customer.officer and customer.address:
        customer.customer_id = ''  # Reset to trigger regeneration
        customer.save()
    else:
        # Delete if no officer or address
        customer.delete()