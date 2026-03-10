# narratives/management/commands/categorize_all_rawtexts.py
"""Run Find Topics (keyword categorization) once on all RawTexts that are not yet COMPLETED."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from narratives.models import RawText
from narratives.models.categories import AppConfiguration
from narratives.utils.categorize import run_find_topics_for_rawtext


class Command(BaseCommand):
    help = "Run categorization (Find topics) on all RawTexts that are NOT_STARTED or OUTDATED (not yet Done)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Run on every RawText (including already COMPLETED).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print count of RawTexts that would be processed.",
        )

    def handle(self, *args, **options):
        run_all = options.get("all", False)
        dry_run = options.get("dry_run", False)

        current_version = AppConfiguration.get_version("categorization_version")

        if run_all:
            qs = RawText.objects.all().order_by("id")
            label = "all"
        else:
            # NOT_STARTED: no version; OUTDATED: version != current
            qs = RawText.objects.filter(
                Q(categorization_version__isnull=True)
                | ~Q(categorization_version=current_version)
            ).order_by("id")
            label = "not yet Done (NOT_STARTED or OUTDATED)"

        total = qs.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"No RawTexts to process ({label}). "
                    "All are already categorized. Use --all to run on every RawText anyway."
                )
            )
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would process {total} RawTexts ({label})."))
            return

        self.stdout.write(f"Processing {total} RawTexts ({label})…")
        done = 0
        created_total = 0
        for rawtext in qs:
            try:
                _sug, created = run_find_topics_for_rawtext(rawtext, reset=False)
                created_total += created
                done += 1
                if done % 50 == 0 or done == total:
                    self.stdout.write(f"  {done}/{total} … ({created_total} PendingTopics created so far)")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  RawText id={rawtext.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {done} RawTexts, created {created_total} PendingTopics."))
