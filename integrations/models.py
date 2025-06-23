from django.db import models
from narratives.models.sources import Source  # if source model lives in narratives

class IntegrationBinding(models.Model):
    source = models.OneToOneField(Source, on_delete=models.CASCADE)
    integration_name = models.CharField(max_length=100)
    integration_config = models.JSONField(default=dict, blank=True)
