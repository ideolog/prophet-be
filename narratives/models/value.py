from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Value(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=Value)
def create_value_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        while Value.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
