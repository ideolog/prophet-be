# Generated by Django 4.2.3 on 2024-09-12 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('narratives', '0031_narrative_modality_negated'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='narrative',
            name='object_identity',
        ),
        migrations.RemoveField(
            model_name='narrative',
            name='object_narrative',
        ),
        migrations.RemoveField(
            model_name='narrative',
            name='subject_identity',
        ),
        migrations.RemoveField(
            model_name='narrative',
            name='subject_narrative',
        ),
        migrations.AddField(
            model_name='narrative',
            name='object_identities',
            field=models.ManyToManyField(blank=True, related_name='obj_identities', to='narratives.identity'),
        ),
        migrations.AddField(
            model_name='narrative',
            name='object_narratives',
            field=models.ManyToManyField(blank=True, related_name='obj_narratives', to='narratives.narrative'),
        ),
        migrations.AddField(
            model_name='narrative',
            name='subject_identities',
            field=models.ManyToManyField(blank=True, related_name='subj_identities', to='narratives.identity'),
        ),
        migrations.AddField(
            model_name='narrative',
            name='subject_narratives',
            field=models.ManyToManyField(blank=True, related_name='subj_narratives', to='narratives.narrative'),
        ),
    ]
