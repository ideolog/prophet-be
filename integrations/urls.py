from django.urls import path
from .views import IntegrationRunView

urlpatterns = [
    path('run/<str:source_slug>/', IntegrationRunView.as_view(), name='integration-run'),
    path("run/<str:source_slug>/<int:page>/", IntegrationRunView.as_view(), name="integration-run-page"),
]
