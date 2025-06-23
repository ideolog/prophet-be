from django.contrib import admin
from django.urls import path, include
from .urls_swagger import urlpatterns as swagger_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('narratives.urls')),
    path('integrations/', include('integrations.urls')),
] + swagger_urls
