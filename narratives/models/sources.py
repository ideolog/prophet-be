from django.db import models
from narratives.models import Person
from django.utils.text import slugify
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
    name = models.CharField(max_length=255, unique=True, help_text="The name of the source, e.g., X, TruthSocial, Whitehouse.gov")
    url = models.URLField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC", help_text="Timezone of the source, e.g. America/New_York")
    slug = models.SlugField(unique=True, blank=True, max_length=300)

    def __str__(self):
        return self.name


class RawText(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="texts")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="texts")
    title = models.CharField(max_length=1000, blank=True, null=True)
    subtitle = models.CharField(max_length=2000, blank=True, null=True)
    content = models.TextField()
    source_url = models.URLField(blank=True, null=True, help_text="Original source URL for reference")
    author = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True, related_name='rawtexts')
    published_at = models.DateTimeField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, max_length=300)
    content_fingerprint = models.CharField(max_length=128, unique=True, blank=True, null=True, help_text="Normalized hash of the content for duplicate detection")

    def __str__(self):
        return f"{(self.title or self.content[:50])[:100]}"

    def save(self, *args, **kwargs):
        if self.content:
            self.content_fingerprint = generate_fingerprint(self.content)
        super().save(*args, **kwargs)


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
