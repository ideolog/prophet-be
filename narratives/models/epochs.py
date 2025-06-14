from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string


class Epoch(models.Model):
    title = models.CharField(max_length=255, unique=True, help_text="E.g., Biden Presidency, Cold War, etc.")
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        if self.end_date:
            return f"{self.title} ({self.start_date} - {self.end_date})"
        return f"{self.title} (Starting {self.start_date})"


@receiver(pre_save, sender=Epoch)
def create_epoch_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.title)
        unique_slug = base_slug
        while Epoch.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
