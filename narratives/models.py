from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

class VerificationStatus(models.Model):
    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending_ai_review', 'Pending AI Review'),
        ('ai_reviewed', 'AI Reviewed'),
        ('user_approved', 'User Approved'),
        ('validator_review', 'Validator Review'),
        ('approved_for_blockchain', 'Approved for Blockchain'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=50, choices=STATUS_CHOICES, unique=True)
    description = models.TextField(blank=True, help_text="Description of the verification status.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Verification Status"
        verbose_name_plural = "Verification Statuses"

    def __str__(self):
        return self.get_name_display()

from django.db import models

class Claim(models.Model):
    text = models.TextField(help_text="The text of the claim submitted by the user.")
    slug = models.SlugField(unique=True, blank=True, max_length=150, help_text="URL-friendly identifier.")
    verification_status = models.ForeignKey(
        'narratives.VerificationStatus',
        on_delete=models.PROTECT,
        related_name="claims"
    )
    status_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.text)[:150]  # Limit slug length to 150
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text[:50]

class SchoolOfThoughtType(models.Model):
    # The name of the type (e.g., Theory, Scientific Discipline, Ideology, Religion)
    name = models.CharField(max_length=255, unique=True)

    # Optional description field to explain the type
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class SchoolOfThought(models.Model):
    # Name of the school of thought (e.g., Liberalism, Rationalism, etc.)
    name = models.CharField(max_length=255, unique=True)

    # Description of the school of thought
    description = models.TextField(blank=True, null=True)

    # Link to the SchoolOfThoughtType model to categorize the school
    type = models.ForeignKey(SchoolOfThoughtType, on_delete=models.CASCADE, related_name='schools_of_thought')

    # Optional: Parent relationship for hierarchical classification
    parent_school = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='sub_schools')

    # Slug for URL-friendly representation
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name


class Value(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name


class Narrative(models.Model):
    description = models.TextField()
    slug = models.SlugField(unique=True, blank=True, max_length=1024)
    values = models.ManyToManyField('Value', blank=True, related_name='narratives')

    # Many-to-Many for multiple identities and narratives as subjects/objects
    subject_identities = models.ManyToManyField('Category', blank=True, related_name="subj_identities")
    subject_narratives = models.ManyToManyField('Narrative', blank=True, related_name="subj_narratives")

    object_identities = models.ManyToManyField('Category', blank=True, related_name="obj_identities")
    object_narratives = models.ManyToManyField('Narrative', blank=True, related_name="obj_narratives")

    action = models.ForeignKey('Action', blank=True, null=True, on_delete=models.CASCADE,
                               related_name="action_of_narrative")
    time = models.ForeignKey('ActionTime', blank=True, null=True, on_delete=models.CASCADE)
    modality = models.ForeignKey('Modality', blank=True, null=True, on_delete=models.CASCADE)
    modality_negated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # First, save the object to get an ID
        super().save(*args, **kwargs)

        # Now validate the many-to-many relationships
        if self.subject_identities.exists() and self.subject_narratives.exists():
            raise ValidationError("A Narrative can have either subject_identities or subject_narratives, but not both.")
        if self.object_identities.exists() and self.object_narratives.exists():
            raise ValidationError("A Narrative can have either object_identities or object_narratives, but not both.")

    def __str__(self):
        return f"{self.slug} ({self.modality.name if self.modality else 'no modality'})"


class Prediction(models.Model):
    narrative = models.ForeignKey('Narrative', on_delete=models.CASCADE)
    earliest_start_date = models.DateField(blank=True, null=True)
    latest_start_date = models.DateField(blank=True, null=True)
    earliest_end_date = models.DateField(blank=True, null=True)
    latest_end_date = models.DateField(blank=True, null=True)
    minimum_value = models.FloatField(blank=True, null=True)
    maximum_value = models.FloatField(blank=True, null=True)
   # value_unit = models.CharField(max_length=255, blank=True)

    def clean(self):
        # Ensure that either date prediction or value prediction is provided, but not both
        date_fields = [self.earliest_start_date, self.latest_start_date, self.earliest_end_date, self.latest_end_date]
        value_fields = [self.minimum_value, self.maximum_value]

        if any(date_fields) and any(value_fields):
            raise ValidationError("A Prediction can have either date predictions or value predictions, but not both.")
        if not any(date_fields) and not any(value_fields):
            raise ValidationError("A Prediction must have either date predictions or value predictions.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Call the clean method before saving
        super().save(*args, **kwargs)

    def __str__(self):
        if self.earliest_start_date and self.latest_end_date:
            return f"{self.narrative.slug} between {self.earliest_start_date} and {self.latest_end_date}"
        elif self.earliest_start_date:
            return f"{self.narrative.slug} after {self.earliest_start_date}"
        elif self.latest_end_date:
            return f"{self.narrative.slug} before {self.latest_end_date}"
        else:
            if self.minimum_value and self.maximum_value:
                return f"{self.narrative.slug} between {self.minimum_value} and {self.maximum_value} {self.value_unit}"
            elif self.minimum_value:
                return f"{self.narrative.slug} greater than {self.minimum_value} {self.value_unit}"
            elif self.maximum_value:
                return f"{self.narrative.slug} less than {self.maximum_value} {self.value_unit}"
            else:
                return f"{self.narrative.slug} with unknown time or value"


class CategoryType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    values = models.ManyToManyField('Value', blank=True, related_name='categories')
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')

    # Many-to-many relationship for locations
    locations = models.ManyToManyField('self', blank=True, related_name='location_for_categories', symmetrical=False)

    # Many-to-many field to associate persons with categories (for events like presidential terms)
    persons = models.ManyToManyField('self', blank=True, related_name='events_for_persons', symmetrical=False)

    # ForeignKey to categorize the category
    category_type = models.ForeignKey(CategoryType, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='categories')

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Action(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    verbs = models.ManyToManyField('Verb', blank=True)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name

class Epoch(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='epochs')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    class Meta:
        unique_together = ('category', 'start_date', 'end_date')  # Ensure uniqueness
    def __str__(self):
        # Display the name of the category and the epoch date range
        if self.end_date:
            return f"{self.category.name} ({self.start_date} - {self.end_date})"
        return f"{self.category.name} (Starting {self.start_date})"


class RelationType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class ActionRelation(models.Model):
    action1 = models.ForeignKey('Action', on_delete=models.CASCADE, related_name="action1")
    action2 = models.ForeignKey('Action', on_delete=models.CASCADE, related_name="action2")
    relation = models.ForeignKey('RelationType', on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['action1', 'action2', 'relation'], name='unique_action_relation')
        ]

    def __str__(self):
        return f"{self.action1.name} {self.relation.name} {self.action2.name}"


class Verb(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class ActionTime(models.Model):
    TIME_CHOICES = (
        ('past', 'Past'),
        ('present', 'Present'),
        ('future', 'Future'),
    )
    start_time_choice = models.CharField(max_length=32, choices=TIME_CHOICES, default='past')
    end_time_choice = models.CharField(max_length=32, choices=TIME_CHOICES, default='future')

    def __str__(self):
        return "{}-{}".format(self.start_time_choice, self.end_time_choice)


@receiver(pre_save, sender=Narrative)
def create_narrative_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.description)
        unique_slug = base_slug
        num = 1
        while Narrative.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


@receiver(pre_save, sender=Category)
def create_category_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        while Category.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


@receiver(pre_save, sender=Action)
def create_action_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        unique_slug = base_slug
        while Action.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug

class Modality(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Examples: "must", "should", "can", "will"
    def __str__(self):
        return self.name

