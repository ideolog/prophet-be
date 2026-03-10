from django.contrib import admin
from .models import *

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'created_at')
    list_display_links = ('id',)
    search_fields = ('creator',)
    list_filter = ('created_at',)
    save_on_top = True

@admin.register(MarketPosition)
class MarketPositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'side', 'shares', 'cost_basis')
    list_display_links = ('user',)
    search_fields = ('user__wallet_address', 'side')
    list_filter = ('side', 'market')
    save_on_top = True

@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('wallet_address', 'created_at', 'updated_at')
    list_display_links = ('wallet_address',)
    search_fields = ('wallet_address',)
    save_on_top = True

@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ('name', 'typical_start_date', 'core_start_date', 'core_end_date', 'typical_end_date')
    list_display_links = ('name',)
    search_fields = ('name',)
    list_filter = ('typical_start_date', 'typical_end_date')
    save_on_top = True

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'topic')
    list_display_links = ('name',)
    search_fields = ('name', 'url')
    save_on_top = True

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name',)
    save_on_top = True

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    list_display_links = ("name",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True

@admin.register(RawText)
class RawTextAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'source', 'genre')
    list_display_links = ('title',)
    search_fields = ('title', 'content', 'author__name')
    list_filter = ('source', 'genre', 'published_at')
    save_on_top = True
