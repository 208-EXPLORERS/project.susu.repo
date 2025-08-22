from django.contrib.auth.decorators import user_passes_test

def officer_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: hasattr(u, 'collectionofficer'),
        login_url='/admin/login/'  # or your login page
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
