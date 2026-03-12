"""
Pre-aggregate topic mention counts by calendar day into TopicMentionDay.

Uses RawText.published_at if set, else RawText.created_at (date only, UTC).
Run periodically (e.g. daily) to keep stats fast for charts and reports.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, F
from django.db.models.functions import Coalesce, TruncDate

from narratives.models import PendingTopic, TopicMentionDay


class Command(BaseCommand):
    help = "Update TopicMentionDay from approved PendingTopics (by article date)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--topic",
            type=int,
            help="Only update this topic id",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be updated",
        )

    def handle(self, *args, **options):
        topic_id = options.get("topic")
        dry_run = options["dry_run"]

        qs = (
            PendingTopic.objects.filter(status="approved")
            .annotate(
                mention_date=TruncDate(
                    Coalesce(F("rawtext__published_at"), F("rawtext__created_at"))
                )
            )
            .values("topic_id", "mention_date")
            .annotate(count=Count("id"))
        )
        if topic_id:
            qs = qs.filter(topic_id=topic_id)

        updated = 0
        created = 0
        for row in qs:
            topic_id = row["topic_id"]
            date = row["mention_date"]
            count = row["count"]
            if date is None:
                continue
            if dry_run:
                self.stdout.write(f"  topic_id={topic_id} date={date} count={count}")
                updated += 1
                continue
            obj, created_flag = TopicMentionDay.objects.update_or_create(
                topic_id=topic_id,
                date=date,
                defaults={"count": count},
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run: would upsert {updated} rows"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done. Created: {created}, updated: {updated}")
            )
