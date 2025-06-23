from django.core.management.base import BaseCommand
from narratives.models import Source

class Command(BaseCommand):
    help = "Populate initial sources"

    def handle(self, *args, **kwargs):
        sources = [
            {
                "name": "The White House",
                "url": "https://www.whitehouse.gov/",
                "slug": "the-white-house",
                "timezone": "America/New_York"
            },
            {
                "name": "Unknown",
                "url": None,
                "slug": "unknown",
                "timezone": "UTC"
            }
        ]

        for src in sources:
            obj, created = Source.objects.get_or_create(
                name=src["name"],
                defaults={
                    "url": src["url"],
                    "slug": src["slug"],
                    "timezone": src["timezone"]
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added: {src['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {src['name']}"))

        self.stdout.write(self.style.SUCCESS("Sources initialized."))
