# Generated by Django 4.2.3 on 2024-09-13 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('narratives', '0035_epoch'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='persons',
            field=models.ManyToManyField(blank=True, related_name='events_for_persons', to='narratives.category'),
        ),
    ]
