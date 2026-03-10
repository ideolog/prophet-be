from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string


class Epoch(models.Model):
    """
    Model for historical/civilizational epochs with fuzzy period boundaries.
    
    Terminology notes:
    - 'typical' is preferred over 'median' because these dates are interpretive scholarly 
      consensus points, not statistical calculations.
    - 'core' is preferred over 'culmination' because the goal is to mark the phase 
      where the epoch is clearly established and dominant, rather than its absolute peak.
    """
    name = models.CharField(max_length=255, unique=True, help_text="Name of the epoch, e.g., 'Modernity', 'The Axial Age'")
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    description = models.TextField(blank=True, null=True)
    notes_on_periodization = models.TextField(blank=True, null=True, help_text="Explanation of why these specific boundaries were chosen")
    source_summary = models.TextField(blank=True, null=True, help_text="Summary of scholarly sources used for this periodization")
    topic = models.OneToOneField('narratives.Topic', on_delete=models.SET_NULL, null=True, blank=True, related_name="epoch_data")

    # Periodization fields (using IntegerField to represent years, allowing BC as negative)
    earliest_start_date = models.IntegerField(
        help_text="Earliest plausible scholarly start (e.g., 1450 for Modernity)"
    )
    typical_start_date = models.IntegerField(
        help_text="Commonly used or representative start (e.g., 1500 for Modernity)"
    )
    core_start_date = models.IntegerField(
        help_text="Point after which the epoch is clearly established or dominant (e.g., 1789 for Modernity)"
    )
    
    core_end_date = models.IntegerField(
        blank=True, null=True, 
        help_text="Point after which the epoch's core form begins to dissolve or transform"
    )
    typical_end_date = models.IntegerField(
        blank=True, null=True, 
        help_text="Commonly used or representative end"
    )
    latest_end_date = models.IntegerField(
        blank=True, null=True, 
        help_text="Latest plausible scholarly end"
    )

    class Meta:
        ordering = ['typical_start_date']
        verbose_name_plural = "Epochs"

    def __str__(self):
        return self.name


@receiver(pre_save, sender=Epoch)
def create_epoch_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name or "epoch")
        unique_slug = base_slug
        while Epoch.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug
