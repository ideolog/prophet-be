# narratives/urls.py

from django.urls import path
from .views import (
    # Sources
    SourceListView,
    SourceDetailView,
    YouTubeSourceAddView,

    # RawText
    RawTextListView,
    RawTextHashDuplicateCheck,
    RawTextListCreateView,
    RawTextMassProcessingView,
    RawTextDetailView,
    RawTextRedownloadView,
    RawTextFindTopicsView,
    RawTextCategorizeAllView,
    RawTextAISuggestTopicsView,
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
    TopicEnhanceWikipediaView,
    DeclinedTopicListView,
    TopicBulkDeleteView,
    TopicDistributionView,
    TopicMergeView,
    TopicTypeListView,
    TopicTypeDetailView,
    AnalyticalFrameworkListView,
    AnalyticalCategoryListView,
    TopicAggregatedDetailView,
    TopicSuggestMergeView,
    EpochListView,
    EpochDetailView,
    ContextSetListView,
    ContextSetDetailView,
)

urlpatterns = [
    # SOURCES
    path('sources/', SourceListView.as_view(), name='source-list-create'),
    path('sources/<str:id>/', SourceDetailView.as_view(), name='source-detail'),
    
    # INTEGRATIONS / HELPERS
    path('youtube/add-channel/', YouTubeSourceAddView.as_view(), name='source-youtube-add'),

    # RAWTEXT
    path('rawtexts/create/', RawTextListCreateView.as_view(), name='rawtext-create'),
    path('rawtexts/check-duplicate/', RawTextHashDuplicateCheck.as_view(), name='rawtext-check-duplicate'),
    path('rawtexts/process-mass/', RawTextMassProcessingView.as_view(), name='rawtext-mass-process'),
    path('rawtexts/<int:id>/', RawTextDetailView.as_view(), name='rawtext-detail'),
    path('rawtexts/<int:id>/redownload/', RawTextRedownloadView.as_view(), name='rawtext-redownload'),
    path('rawtexts/<int:id>/find-topics/', RawTextFindTopicsView.as_view(), name='rawtext-find-topics'),
    path('rawtexts/categorize-all/', RawTextCategorizeAllView.as_view(), name='rawtext-categorize-all'),
    path('rawtexts/<int:id>/ai-suggest/', RawTextAISuggestTopicsView.as_view(), name='rawtext-ai-suggest'),
    path('rawtexts/', RawTextListView.as_view(), name='rawtext-list'),
    path('pending-topics/<int:id>/action/', PendingTopicActionView.as_view(), name='pending-topic-action'),

    # TOPICS
    path('topics/', TopicListView.as_view(), name='topic-list'),
    path('topics/types/', TopicTypeListView.as_view(), name='topic-type-list'),
    path('topics/types/<int:id>/', TopicTypeDetailView.as_view(), name='topic-type-detail'),
    path('analytical-frameworks/', AnalyticalFrameworkListView.as_view(), name='analytical-framework-list'),
    path('analytical-categories/', AnalyticalCategoryListView.as_view(), name='analytical-category-list'),
    path('topics/bulk-delete/', TopicBulkDeleteView.as_view(), name='topic-bulk-delete'),
    path('topics/merge/', TopicMergeView.as_view(), name='topic-merge'),
    path('topics/suggest-merge/', TopicSuggestMergeView.as_view(), name='topic-suggest-merge'),
    path('topics/create/', TopicCreateView.as_view(), name='topic-create'),
    path('topics/<int:id>/', TopicDetailView.as_view(), name='topic-detail'),
    path('topics/<int:id>/aggregated/', TopicAggregatedDetailView.as_view(), name='topic-aggregated-detail'),
    path('topics/<int:id>/enhance-wikipedia/', TopicEnhanceWikipediaView.as_view(), name='topic-enhance-wikipedia'),
    path('topics/<int:id>/distribution/', TopicDistributionView.as_view(), name='topic-distribution'),
    path('declined-topics/', DeclinedTopicListView.as_view(), name='declined-topic-list'),

    # CONTEXT SETS (for weak keyword required_context [SLUG])
    path('context-sets/', ContextSetListView.as_view(), name='context-set-list'),
    path('context-sets/<str:pk_or_slug>/', ContextSetDetailView.as_view(), name='context-set-detail'),

    # EPOCHS
    path('epochs/', EpochListView.as_view(), name='epoch-list'),
    path('epochs/<int:id>/', EpochDetailView.as_view(), name='epoch-detail'),


    # MARKETS
    path("markets/create/<int:claim_id>/", MarketCreateView.as_view(), name="market-create"),
    path("markets/", MarketListView.as_view(), name="market-list"),
    path('markets/<int:market_id>/buy/', MarketBuyView.as_view(), name='market-buy'),

    # ACCOUNTS
    path('auth/login/', WalletLoginView.as_view(), name="wallet-login"),
    path("users/<str:wallet_address>/", UserAccountDetailView.as_view(), name="user-detail"),
    path("users/<str:wallet_address>/positions/", MyPositionsView.as_view(), name="user-positions"),
]
