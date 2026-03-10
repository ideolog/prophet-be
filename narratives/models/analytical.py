"""
Analytical frameworks (SWOT, PESTEL) and their link to Topics.
Threat and PESTEL dimensions are analytical classification, not ontology (TopicType).
"""
from django.db import models
from django.utils.text import slugify


class AnalyticalFramework(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AnalyticalCategory(models.Model):
    framework = models.ForeignKey(
        AnalyticalFramework,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    class Meta:
        ordering = ["framework", "name"]
        unique_together = [["framework", "slug"]]
        verbose_name_plural = "Analytical categories"

    def __str__(self):
        return f"{self.framework.name}: {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TopicAnalyticalCategory(models.Model):
    topic = models.ForeignKey(
        "narratives.Topic",
        on_delete=models.CASCADE,
        related_name="analytical_categories",
    )
    analytical_category = models.ForeignKey(
        AnalyticalCategory,
        on_delete=models.CASCADE,
        related_name="topic_links",
    )
    note = models.TextField(blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic", "analytical_category"]
        unique_together = [["topic", "analytical_category"]]
        verbose_name_plural = "Topic analytical categories"

    def __str__(self):
        return f"{self.topic.name} — {self.analytical_category}"
