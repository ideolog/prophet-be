from django.contrib import admin
from .models import *

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('claim', 'creator', 'created_at')
    list_display_links = ('claim',)
    search_fields = ('claim__text', 'creator')
    list_filter = ('created_at',)
    save_on_top = True

@admin.register(MarketPosition)
class MarketPositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'side', 'shares', 'cost_basis')
    list_display_links = ('user',)
    search_fields = ('user__wallet_address', 'market__claim__text', 'side')
    list_filter = ('side', 'market')
    save_on_top = True

@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('wallet_address', 'verification_status', 'created_at', 'updated_at')
    list_display_links = ('wallet_address',)
    search_fields = ('wallet_address',)
    list_filter = ('verification_status',)
    save_on_top = True

@admin.register(VerificationStatus)
class VerificationStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('text', 'verification_status', 'created_at')
    list_display_links = ('text',)
    search_fields = ('text',)
    save_on_top = True

@admin.register(SchoolOfThoughtType)
class SchoolOfThoughtTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(SchoolOfThought)
class SchoolOfThoughtAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'description')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    list_display_links = ('name',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True

@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date')
    list_display_links = ('title',)
    search_fields = ('title',)
    list_filter = ('start_date', 'end_date')
    save_on_top = True

# ✅ NEW MODELS:

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')
    list_display_links = ('name',)
    search_fields = ('name', 'url')
    save_on_top = True

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name',)
    save_on_top = True

@admin.register(RawText)
class RawTextAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'source', 'genre')
    list_display_links = ('title',)
    search_fields = ('title', 'content', 'author')
    list_filter = ('source', 'genre', 'published_at')
    save_on_top = True
