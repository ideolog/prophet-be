"""
Load value topics from a CSV file.

CSV columns: name (required), slug (optional), description (optional).
Creates Topic with topic_type = TopicType "Value" for each row.
Use this to restore the list of values after the old Value model was removed (migration 0094).
"""
import csv
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType


class Command(BaseCommand):
    help = "Load values from CSV into Topics with topic_type=Value"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to CSV with columns: name [, slug, description]",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]

        value_type, created = TopicType.objects.get_or_create(
            name="Value",
            defaults={"description": "Human and systemic values, principles, ethics"},
        )
        if created:
            self.stdout.write(self.style.WARNING("Created TopicType 'Value'"))

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if "name" not in (reader.fieldnames or []):
                    self.stdout.write(
                        self.style.ERROR("CSV must have a 'name' column")
                    )
                    return
                created_count = 0
                skipped = 0
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        continue
                    slug = (row.get("slug") or "").strip() or None
                    description = (row.get("description") or "").strip() or None

                    if dry_run:
                        exists = Topic.objects.filter(name=name).exists()
                        self.stdout.write(
                            f"  {'(exists)' if exists else 'CREATE'}: {name}"
                        )
                        if not exists:
                            created_count += 1
                        continue

                    topic, created = Topic.objects.get_or_create(
                        name=name,
                        defaults={
                            "topic_type": value_type,
                            "description": description,
                        },
                    )
                    if created:
                        if slug:
                            topic.slug = slug
                            topic.save()
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f"  Created: {name}"))
                    else:
                        if topic.topic_type_id != value_type.id:
                            topic.topic_type = value_type
                            if description and not topic.description:
                                topic.description = description
                            topic.save()
                            self.stdout.write(
                                self.style.WARNING(f"  Updated type to Value: {name}")
                            )
                        else:
                            skipped += 1

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f"Dry run: would create {created_count} topics")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Done. Created: {created_count}, skipped (already exist): {skipped}"
                        )
                    )
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
            raise
