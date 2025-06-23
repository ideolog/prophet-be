from django.contrib import admin
from .models import IntegrationBinding

@admin.register(IntegrationBinding)
class IntegrationBindingAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'integration_name']
    search_fields = ['source__name', 'integration_name']
