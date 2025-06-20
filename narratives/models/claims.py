from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from narratives.utils.text import generate_fingerprint
from narratives.models import Person  # ✅ we reuse existing Person model

class VerificationStatus(models.Model):
    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending_ai_review', 'Pending AI Review'),
        ('market_created', 'Market Created'),
        ('ai_reviewed', 'AI Reviewed'),
        ('user_approved', 'User Approved'),
        ('ai_variants_generated', 'AI Variants Generated'),
        ('validator_review', 'Validator Review'),
        ('approved_for_blockchain', 'Approved for Blockchain'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=50, choices=STATUS_CHOICES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Verification Status"
        verbose_name_plural = "Verification Statuses"

    def __str__(self):
        return self.get_name_display()


class Claim(models.Model):
    text = models.TextField(unique=True)
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    verification_status = models.ForeignKey('VerificationStatus', on_delete=models.PROTECT, related_name="claims")
    status_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    submitter = models.CharField(max_length=255)  # ✅ renamed from author
    attributed_persons = models.ManyToManyField(Person, blank=True, related_name="associated_claims")

    parent_claim = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="ai_variants")
    generated_by_ai = models.BooleanField(default=False)
    ai_model = models.CharField(max_length=50, blank=True, null=True)
    content_fingerprint = models.CharField(max_length=128, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.text)[:150]
            unique_slug = base_slug
            while Claim.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{get_random_string(5)}"
            self.slug = unique_slug

        if self.text and not self.content_fingerprint:
            self.content_fingerprint = generate_fingerprint(self.text)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.text[:50]
