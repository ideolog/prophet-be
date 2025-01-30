from django.urls import path
from .views import NarrativeListView, ClaimListCreateView, ClaimDetailView, WalletLoginView, MarketCreateView

urlpatterns = [
    path('narratives/', NarrativeListView.as_view(), name='narrative-list'),
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('claims/<int:claim_id>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('auth/login/', WalletLoginView.as_view(), name="wallet-login"),
    path("markets/create/<int:claim_id>/", MarketCreateView.as_view(), name="market-create"),
]
