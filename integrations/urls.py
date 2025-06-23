from django.urls import path
from .views import IntegrationRunView

urlpatterns = [
    path('run/<slug:source_slug>/', IntegrationRunView.as_view(), name='integration-run'),
    path("run/<slug:source_slug>/<int:page>/", IntegrationRunView.as_view(), name="integration-run-page"),
]
