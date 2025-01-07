from django.core.management.base import BaseCommand
from narratives.models import Epoch
from collections import defaultdict

class Command(BaseCommand):
    help = 'Deduplicate epochs with the same category, start date, and end date'

    def handle(self, *args, **kwargs):
        epochs_by_key = defaultdict(list)

        # Group epochs by (category, start_date, end_date)
        for epoch in Epoch.objects.all():
            key = (epoch.category.id, epoch.start_date, epoch.end_date)
            epochs_by_key[key].append(epoch)

        # Iterate over the grouped epochs and remove duplicates
        for key, epochs in epochs_by_key.items():
            if len(epochs) > 1:
                primary_epoch = epochs[0]
                duplicates = epochs[1:]
                for duplicate in duplicates:
                    duplicate.delete()

                self.stdout.write(self.style.SUCCESS(f"Deduplicated epoch for {primary_epoch.category} from {primary_epoch.start_date} to {primary_epoch.end_date}"))

