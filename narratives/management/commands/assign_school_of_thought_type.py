# narratives/management/commands/assign_school_of_thought_type.py
"""One-time: assign TopicType 'School of thought' to all Topics that are used as a school of thought for at least one other topic."""

from django.core.management.base import BaseCommand
from django.db.models import Count

from narratives.models import Topic
from narratives.utils.school_of_thought import get_school_of_thought_type


class Command(BaseCommand):
    help = "Assign type 'School of thought' to every Topic that is listed as school of thought for at least one other topic."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print which topics would be updated.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        sot_type = get_school_of_thought_type()
        if not sot_type:
            self.stdout.write(self.style.ERROR("TopicType 'School of thought' not found. Create it first (e.g. in admin)."))
            return

        # Topics that are used as school by at least one other topic (reverse relation topics_in_school)
        school_topics = Topic.objects.annotate(
            n_topics_using_as_school=Count("topics_in_school")
        ).filter(n_topics_using_as_school__gt=0)

        to_update = [t for t in school_topics if t.topic_type_id != sot_type.id]
        if not to_update:
            self.stdout.write(self.style.SUCCESS("No topics to update: all topics used as School of thought already have that type."))
            return

        if dry_run:
            for t in to_update:
                self.stdout.write(f"  Would set type to 'School of thought': {t.name} (id={t.id})")
            self.stdout.write(self.style.SUCCESS(f"Dry run: {len(to_update)} topics would be updated."))
            return

        updated = 0
        for t in to_update:
            t.topic_type = sot_type
            t.save(update_fields=["topic_type_id"])
            self.stdout.write(self.style.SUCCESS(f"  {t.name} (id={t.id})"))
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Done. Assigned 'School of thought' to {updated} topics."))
