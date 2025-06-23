from django.core.management.base import BaseCommand
from narratives.models import Genre

GENRES = [
    "speech",
    "press_release",
    "fact_sheet",
    "other"
]

class Command(BaseCommand):
    help = "Populate initial genres"

    def handle(self, *args, **kwargs):
        for name in GENRES:
            Genre.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Genres initialized"))
