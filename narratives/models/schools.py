from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string



class SchoolOfThoughtType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class SchoolOfThought(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    type = models.ForeignKey(SchoolOfThoughtType, on_delete=models.CASCADE, related_name='schools_of_thought')
    parent_school = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='sub_schools')
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name


@receiver(pre_save, sender=SchoolOfThought)
def create_schoolofthought_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        while SchoolOfThought.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
