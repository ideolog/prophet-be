from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save
from narratives.utils.text import generate_fingerprint
from django.dispatch import receiver


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="E.g., tweet, speech, poem, proclamation")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Source(models.Model):
    PLATFORM_CHOICES = [
        ('direct', 'Direct/RSS'),
        ('youtube', 'YouTube Channel'),
        ('twitter', 'Twitter/X Account'),
        ('telegram', 'Telegram Channel'),
    ]

    name = models.CharField(max_length=255, unique=True, help_text="The name of the source, e.g., Vitalik Buterin")
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='direct')
    handle = models.CharField(max_length=255, blank=True, null=True, help_text="Handle of the channel/account, e.g., @vitalik")
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="External ID of the channel/account")
    description = models.TextField(blank=True, null=True, help_text="Description of the channel/source")
    subscriber_count = models.PositiveIntegerField(default=0, help_text="Number of subscribers/followers")
    avatar_url = models.URLField(blank=True, null=True, help_text="URL of the channel/source avatar image")

    is_new = models.BooleanField(default=True, help_text="Whether this source was just added")
    created_at = models.DateTimeField(default=timezone.now)

    topic = models.ForeignKey('narratives.Topic', on_delete=models.SET_NULL, blank=True, null=True, related_name="sources")

    url = models.URLField(blank=True, null=True)
    rss_url = models.URLField(blank=True, null=True, help_text="Optional RSS feed URL for this source")
    avatar_file = models.ImageField(upload_to='sources/avatars/', blank=True, null=True, help_text="Uploaded avatar image")
    timezone = models.CharField(max_length=50, default="UTC", help_text="Timezone of the source, e.g. America/New_York")
    slug = models.SlugField(unique=True, blank=True, max_length=300)

    def __str__(self):
        return f"{self.name} ({self.platform})"


class RawText(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="texts")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="texts")
    title = models.CharField(max_length=1000, blank=True, null=True)
    subtitle = models.CharField(max_length=2000, blank=True, null=True)
    content = models.TextField()
    source_url = models.URLField(blank=True, null=True, help_text="Original source URL for reference")
    author = models.ForeignKey('narratives.Topic', on_delete=models.SET_NULL, blank=True, null=True, related_name='authored_rawtexts')
    published_at = models.DateTimeField(blank=True, null=True)
    is_new = models.BooleanField(default=True, help_text="Whether this article was just imported")
    is_updated = models.BooleanField(default=False, help_text="Whether this article was updated with new info")
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.SlugField(unique=True, blank=True, max_length=300)
    content_fingerprint = models.CharField(max_length=128, unique=True, blank=True, null=True, help_text="Normalized hash of the content for duplicate detection")

    # Categorization Versioning
    categorization_version = models.CharField(max_length=20, blank=True, null=True, help_text="The version of the categorization logic used")
    last_categorized_at = models.DateTimeField(blank=True, null=True)

    @property
    def categorization_status(self):
        from .categories import AppConfiguration
        current_version = AppConfiguration.get_version("categorization_version")
        if not self.categorization_version:
            return "NOT_STARTED"
        if self.categorization_version != current_version:
            return "OUTDATED"
        if self.pending_topics.filter(status='pending').exists():
            return "PENDING_REVIEW"
        return "COMPLETED"

    def __str__(self):
        return f"{(self.title or self.content[:50])[:100]}"

    def save(self, *args, **kwargs):
        if self.content:
            self.content_fingerprint = generate_fingerprint(self.content)
        super().save(*args, **kwargs)


class RawTextProcessing(models.Model):
    rawtext = models.ForeignKey(RawText, on_delete=models.CASCADE, related_name="processing_records")
    model_used = models.CharField(max_length=255, help_text="Which AI model was used, e.g., 'gpt-4o'")
    processed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='SUCCESS')
    notes = models.TextField(blank=True, null=True, help_text="Optional notes, e.g., error messages or warnings")

    def __str__(self):
        return f"{self.rawtext.slug} - {self.model_used} ({self.status})"


class PendingTopic(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    rawtext = models.ForeignKey(RawText, on_delete=models.CASCADE, related_name="pending_topics")
    topic = models.ForeignKey('narratives.Topic', on_delete=models.CASCADE, related_name="pending_rawtexts")
    matched_keyword = models.CharField(max_length=255, blank=True, null=True, help_text="The exact keyword that triggered the match")
    is_weak = models.BooleanField(default=False, help_text="Whether this match was from a weak keyword")
    found_context_words = models.JSONField(default=list, blank=True, help_text="List of context words found near the weak keyword")
    context = models.TextField(help_text="The sentence or snippet where the topic was found")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rawtext.id} -> {self.topic.name} ({self.status})"


# Slug creation signal (safely updated)
@receiver(pre_save, sender=Source)
@receiver(pre_save, sender=RawText)
def create_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(getattr(instance, "title", None) or getattr(instance, "name", None) or instance.content[:50])
        base_slug = base_slug[:250]  # Limit base slug length safely
        unique_slug = base_slug
        while sender.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
            unique_slug = unique_slug[:300]  # Fully limit to DB field
        instance.slug = unique_slug
