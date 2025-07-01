# narratives/urls.py

from django.urls import path
from .views import (
    # Claims
    ClaimListCreateView,
    ClaimDetailView,
    GenerateClaimsFromTextView,

    # RawText
    RawTextHashDuplicateCheck,
    RawTextCreateView,
    RawTextMassProcessingView,

    # Markets
    MarketCreateView,
    MarketListView,
    MarketBuyView,

    # Accounts
    WalletLoginView,
    UserAccountDetailView,
    MyPositionsView,
)

urlpatterns = [
    # CLAIMS
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('claims/<int:claim_id>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('claims/generate-from-text/', GenerateClaimsFromTextView.as_view(), name='generate-claims-from-text'),

    # RAWTEXT
    path('rawtexts/', RawTextCreateView.as_view(), name='rawtext-create'),
    path('rawtexts/check-duplicate/', RawTextHashDuplicateCheck.as_view(), name='rawtext-check-duplicate'),
    path("rawtexts/process-mass/", RawTextMassProcessingView.as_view(), name="rawtext-mass-process"),


    # MARKETS
    path("markets/create/<int:claim_id>/", MarketCreateView.as_view(), name="market-create"),
    path("markets/", MarketListView.as_view(), name="market-list"),
    path('markets/<int:market_id>/buy/', MarketBuyView.as_view(), name='market-buy'),

    # ACCOUNTS
    path('auth/login/', WalletLoginView.as_view(), name="wallet-login"),
    path("users/<str:wallet_address>/", UserAccountDetailView.as_view(), name="user-detail"),
    path("users/<str:wallet_address>/positions/", MyPositionsView.as_view(), name="user-positions"),
]
