from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Location(models.Model):
    class LocationTypeChoices(models.TextChoices):
        CONTINENT = "continent", "Continent"
        COUNTRY = "country", "Country"
        REGION = "region", "Region"
        STATE = "state", "State"
        PROVINCE = "province", "Province"
        CITY = "city", "City"
        COUNTY = "county", "County"
        DISTRICT = "district", "District"
        TERRITORY = "territory", "Territory"

    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=50, choices=LocationTypeChoices.choices)
    parent_location = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name="sub_locations")
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=Location)
def create_location_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        while Location.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


class Topic(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)

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
@receiver(pre_save, sender=Person)
@receiver(pre_save, sender=Organization)
def create_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(getattr(instance, 'name', None) or getattr(instance, 'full_name'))
        unique_slug = base_slug
        ModelClass = sender
        while ModelClass.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
