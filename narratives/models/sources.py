from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="E.g., tweet, speech, poem, proclamation")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Source(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="The name of the source, e.g., X, TruthSocial, Whitehouse.gov")
    url = models.URLField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name


class RawText(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="texts")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="texts")
    title = models.CharField(max_length=255, blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    author = models.CharField(max_length=255, blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return f"{self.title or self.content[:50]}"


# Slug creation signals
@receiver(pre_save, sender=Source)
@receiver(pre_save, sender=RawText)
def create_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(getattr(instance, "name", None) or getattr(instance, "title", None) or instance.content[:50])
        unique_slug = base_slug
        ModelClass = sender
        while ModelClass.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
