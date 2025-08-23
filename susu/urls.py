from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),  # Django admin moved to different path
    path('', include('core.urls')),  # Your app handles everything else
]