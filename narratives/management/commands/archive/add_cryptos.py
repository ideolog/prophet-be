from django.core.management.base import BaseCommand
import csv
from narratives.models import Identity  # Replace with your app and model name


class Command(BaseCommand):
    help = 'Add top 100 cryptocurrencies to the Identity model'

    def handle(self, *args, **kwargs):
        csv_file_path = 'top_100_cryptocurrencies.csv'  # Replace with the correct path

        with open(csv_file_path, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row

            for row in reader:
                crypto_name = row[0]
                Identity.objects.get_or_create(name=crypto_name)
                self.stdout.write(self.style.SUCCESS(f'Successfully added {crypto_name}'))
