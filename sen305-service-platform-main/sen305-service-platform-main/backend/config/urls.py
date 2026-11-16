from django.conf.urls import include
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include('django.contrib.auth.urls')),
    path("requests/", include('requests_app.urls')),
    path("", include('core.urls'))
]
