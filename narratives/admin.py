from django.contrib import admin
from .models import *

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('claim', 'creator', 'created_at')  # Adjust fields as needed
    list_display_links = ('claim',)
    search_fields = ('claim__text', 'creator')  # Allows searching by claim text and creator
    list_filter = ('created_at',)
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
    list_display = ('name', 'description')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(SchoolOfThought)
class SchoolOfThoughtAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'type')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    save_on_top = True

@admin.register(Narrative)
class NarrativeAdmin(admin.ModelAdmin):
    list_display = ('slug', )
    list_display_links = ('slug',)
    search_fields = ('slug', 'description')
    save_on_top = True

@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')  # Display name, slug, and description in the list view
    list_display_links = ('name', 'slug')  # Make name and slug clickable
    search_fields = ('name', 'slug', 'description')  # Enable search by name, slug, and description
    prepopulated_fields = {"slug": ("name",)}  # Automatically generate slug from name
    save_on_top = True  # Save button at the top of the page

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'parent')  # Display important fields
    search_fields = ('name', 'category_type__name')     # Allow searching by name and type
    list_filter = ('category_type',)                    # Add filtering by category type
    filter_horizontal = ('locations',)                  # Enable horizontal filter for many-to-many fields

    # Optional: Customize form fields if necessary
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category_type', 'parent', 'locations')
        }),
    )

@admin.register(CategoryType)
class CategoryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_display_links = ('name',)
    search_fields = ('name',)
    save_on_top = True

@admin.register(ActionTime)
class ActionTime(admin.ModelAdmin):
    list_display = ('__str__', 'start_time_choice', 'end_time_choice')
    save_on_top = True

@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_display_links = ('name',)
    search_fields = ('name',)
    save_on_top = True

@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ('category', 'start_date', 'end_date')  # Display category, start, and end date
    search_fields = ('category__name',)  # Enable search by category name
    list_filter = ('start_date', 'end_date')  # Filter epochs by date range

@admin.register(ActionRelation)
class ActionRelationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'relation')
    save_on_top = True

@admin.register(Verb)
class VerbAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_display_links = ('name',)
    search_fields = ('name',)
    save_on_top = True

@admin.register(Modality)
class ModalityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    save_on_top = True
