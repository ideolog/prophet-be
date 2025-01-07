from django.urls import path
from .views import NarrativeListView, ClaimListCreateView

urlpatterns = [
    path('narratives/', NarrativeListView.as_view(), name='narrative-list'),
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
]
