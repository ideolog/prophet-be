from django.contrib import admin
from .models import *

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('claim', 'creator', 'created_at')  # Adjust fields as needed
    list_display_links = ('claim',)
    search_fields = ('claim__text', 'creator')  # Allows searching by claim text and creator
    list_filter = ('created_at',)
    save_on_top = True

@admin.register(MarketPosition)
class MarketPositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'side', 'shares', 'cost_basis')
    list_display_links = ('user',)
    search_fields = (
        'user__wallet_address',
        'market__claim__text',
        'side',
    )
    list_filter = ('side', 'market')
    save_on_top = True

@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('wallet_address', 'verification_status', 'created_at', 'updated_at')  # Display key fields in the list view
    list_display_links = ('wallet_address',)  # Make wallet address clickable
    search_fields = ('wallet_address',)  # Enable search by wallet address
    list_filter = ('verification_status',)  # Allow filtering by verification status
    save_on_top = True  # Save button at the top of the page

@admin.register(VerificationStatus)
class VerificationStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('text',)
    list_display_links = ('text',)
    search_fields = ('text',)
    save_on_top = True

@admin.register(SchoolOfThoughtType)
class SchoolOfThoughtTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'description')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(SchoolOfThought)
class SchoolOfThoughtAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'description', 'type')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')  # Display name, slug, and description in the list view
    list_display_links = ('name', 'slug')  # Make name and slug clickable
    search_fields = ('name', 'slug', 'description')  # Enable search by name, slug, and description
    prepopulated_fields = {"slug": ("name",)}  # Automatically generate slug from name
    save_on_top = True  # Save button at the top of the page


@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date')  # Display category, start, and end date
    search_fields = ('category__name',)  # Enable search by category name
    list_filter = ('start_date', 'end_date')  # Filter epochs by date range

