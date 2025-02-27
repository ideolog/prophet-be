# Generated by Django 4.2.3 on 2024-02-28 01:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('narratives', '0009_rename_actors_actor_narrative_object_actor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='narrative',
            name='object_actor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='object_in_narratives', to='narratives.actor'),
        ),
        migrations.AlterField(
            model_name='narrative',
            name='object_identity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='object_in_narratives', to='narratives.identity'),
        ),
        migrations.AlterField(
            model_name='narrative',
            name='subject_actor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subject_in_narratives', to='narratives.actor'),
        ),
        migrations.AlterField(
            model_name='narrative',
            name='subject_identity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subject_in_narratives', to='narratives.identity'),
        ),
    ]
