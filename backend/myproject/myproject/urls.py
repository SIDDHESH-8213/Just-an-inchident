from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('race_strategy.urls')),  # Include the race_strategy app URLs
]
