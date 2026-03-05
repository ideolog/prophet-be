# narratives/urls.py

from django.urls import path
from .views import (
    # Sources
    SourceListView,
    SourceDetailView,
    YouTubeSourceAddView,

    # Claims
    ClaimListCreateView,
    ClaimDetailView,
    GenerateClaimsFromTextView,

    # RawText
    RawTextHashDuplicateCheck,
    RawTextListCreateView,
    RawTextMassProcessingView,
    RawTextDetailView,
    RawTextRedownloadView,
    RawTextFindTopicsView,
    PendingTopicActionView,

    # Markets
    MarketCreateView,
    MarketListView,
    MarketBuyView,

    # Accounts
    WalletLoginView,
    UserAccountDetailView,
    MyPositionsView,

    # Topics
    TopicListView,
    TopicCreateView,
    TopicDetailView,
)

urlpatterns = [
    # SOURCES
    path('sources/', SourceListView.as_view(), name='source-list-create'),
    path('sources/<int:id>/', SourceDetailView.as_view(), name='source-detail'),
    path('sources/youtube-add/', YouTubeSourceAddView.as_view(), name='source-youtube-add'),

    # CLAIMS
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('claims/<int:claim_id>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('claims/generate-from-text/', GenerateClaimsFromTextView.as_view(), name='generate-claims-from-text'),

    # RAWTEXT
    path('rawtexts/', RawTextListCreateView.as_view(), name='rawtext-create'),
    path('rawtexts/check-duplicate/', RawTextHashDuplicateCheck.as_view(), name='rawtext-check-duplicate'),
    path('rawtexts/process-mass/', RawTextMassProcessingView.as_view(), name='rawtext-mass-process'),
    path('rawtexts/<int:id>/', RawTextDetailView.as_view(), name='rawtext-detail'),
    path('rawtexts/<int:id>/redownload/', RawTextRedownloadView.as_view(), name='rawtext-redownload'),
    path('rawtexts/<int:id>/find-topics/', RawTextFindTopicsView.as_view(), name='rawtext-find-topics'),
    path('pending-topics/<int:id>/action/', PendingTopicActionView.as_view(), name='pending-topic-action'),

    # TOPICS
    path('topics/', TopicListView.as_view(), name='topic-list'),
    path('topics/create/', TopicCreateView.as_view(), name='topic-create'),
    path('topics/<int:id>/', TopicDetailView.as_view(), name='topic-detail'),


    # MARKETS
    path("markets/create/<int:claim_id>/", MarketCreateView.as_view(), name="market-create"),
    path("markets/", MarketListView.as_view(), name="market-list"),
    path('markets/<int:market_id>/buy/', MarketBuyView.as_view(), name='market-buy'),

    # ACCOUNTS
    path('auth/login/', WalletLoginView.as_view(), name="wallet-login"),
    path("users/<str:wallet_address>/", UserAccountDetailView.as_view(), name="user-detail"),
    path("users/<str:wallet_address>/positions/", MyPositionsView.as_view(), name="user-positions"),
]
