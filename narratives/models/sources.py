from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save
from django.dispatch import receiver
import unicodedata
import hashlib
import string
import re

def generate_fingerprint(text):
    text = text.strip()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))  # remove diacritics
    text = ''.join(c for c in text if c.isprintable() and not unicodedata.category(c).startswith('C'))  # remove control chars
    text = re.sub(r'\W+', '', text.lower())  # strip punctuation, lowercase
    return hashlib.md5(text.encode('utf-8')).hexdigest()



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
    content_fingerprint = models.CharField(max_length=128, unique=True, blank=True, null=True, help_text="Normalized hash of the content for duplicate detection")

    def __str__(self):
        return f"{self.title or self.content[:50]}"


# Slug creation signals
@receiver(pre_save, sender=Source)
@receiver(pre_save, sender=RawText)
def create_slug_and_fingerprint(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(getattr(instance, "title", None) or getattr(instance, "name", None) or instance.content[:50])
        unique_slug = base_slug
        while sender.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug

    if isinstance(instance, RawText) and not instance.content_fingerprint and instance.content:
        instance.content_fingerprint = generate_fingerprint(instance.content)


