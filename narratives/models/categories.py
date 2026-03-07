from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver


class AppConfiguration(models.Model):
    key = models.CharField(max_length=100, unique=True, help_text="Config key, e.g., 'categorization_version'")
    value = models.CharField(max_length=255, help_text="Config value")
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_version(cls, key, default="0.001"):
        config, _ = cls.objects.get_or_create(
            key=key, 
            defaults={"value": default, "description": f"Version for {key.replace('_', ' ')}"}
        )
        return config.value

    @classmethod
    def increment_version(cls, key):
        config, created = cls.objects.get_or_create(
            key=key, 
            defaults={"value": "0.001", "description": f"Version for {key.replace('_', ' ')}"}
        )
        if not created:
            try:
                current_val = float(config.value)
                # Increment by 0.001
                new_val = f"{current_val + 0.001:.3f}"
                config.value = new_val
                config.save()
            except ValueError:
                # If not a float, just keep it as is or reset
                pass
        return config.value


class Topic(models.Model):
    name = models.CharField(max_length=500, unique=True)
    alternative_name = models.CharField(max_length=500, blank=True, null=True, help_text="Alternative name for this topic (e.g., Freedom of Expression for Freedom of Speech)")
    slug = models.SlugField(unique=True, blank=True, max_length=500)
    parents = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="children")
    related_topics = models.ManyToManyField('self', symmetrical=True, blank=True, related_name="related_to")
    schools_of_thought = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="topics_in_school", help_text="Schools of thought that this topic belongs to or is defined by")
    description = models.TextField(blank=True, null=True)
    keywords = models.JSONField(default=list, blank=True, help_text="Strong keywords (no AI check needed)")
    weak_keywords = models.JSONField(
        default=list, 
        blank=True, 
        help_text="List of dicts: [{'keyword': 'gas', 'required_context': ['blockchain'], 'distance': 10}]"
    )
    is_placeholder = models.BooleanField(default=False, help_text="If true, this topic will not be searched in texts (used only for hierarchy)")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data for specific types (e.g., bio for persons)")

    def __str__(self):
        return self.name


class Person(models.Model):
    full_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.full_name


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name


# Signal receivers for slugs
@receiver(pre_save, sender=Topic)
def create_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        ModelClass = sender
        while ModelClass.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


@receiver([post_save, post_delete], sender=Topic)
def increment_categorization_version(sender, instance, **kwargs):
    # Only increment if not a new Topic with no keywords (to avoid double increment on creation if keywords added later)
    # Actually, any change to Topic (name, keywords, etc.) should invalidate.
    AppConfiguration.increment_version("categorization_version")
