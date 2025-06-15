from django.urls import path
from .views import (
    ClaimListCreateView,
    ClaimDetailView,
    WalletLoginView,
    MarketCreateView,
    MarketListView,
    MarketBuyView,
    UserAccountDetailView,
    MyPositionsView,
    GenerateClaimsFromTextView,
    # RawtextDuplicateCheckView,
)

urlpatterns = [
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('claims/<int:claim_id>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('claims/generate-from-text/', GenerateClaimsFromTextView.as_view(), name='generate-claims-from-text'),
    path('auth/login/', WalletLoginView.as_view(), name="wallet-login"),
    path("markets/create/<int:claim_id>/", MarketCreateView.as_view(), name="market-create"),
    path("markets/", MarketListView.as_view(), name="market-list"),
    path('markets/<int:market_id>/buy/', MarketBuyView.as_view(), name='market-buy'),
    path("users/<str:wallet_address>/", UserAccountDetailView.as_view(), name="user-detail"),
    path("users/<str:wallet_address>/positions/", MyPositionsView.as_view(), name="user-positions"),

    # path('rawtext/duplicate-check/', RawtextDuplicateCheckView.as_view(), name='rawtext-duplicate-check')
]
