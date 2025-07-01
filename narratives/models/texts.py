from django.db import models
from django.utils import timezone


class RawTextProcessing(models.Model):
    rawtext = models.ForeignKey(RawText, on_delete=models.CASCADE, related_name="processing_records")
    model_used = models.CharField(max_length=255, help_text="Which AI model was used, e.g., 'gpt-4o'")
    processed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='SUCCESS')
    notes = models.TextField(blank=True, null=True, help_text="Optional notes, e.g., error messages or warnings")

    def __str__(self):
        return f"{self.rawtext.slug} - {self.model_used} ({self.status})"
