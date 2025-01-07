import csv
from django.core.management.base import BaseCommand
from narratives.models import Value  # Replace 'your_app' with the name of your Django app

class Command(BaseCommand):
    help = 'Load values from a CSV file into the Value model'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file containing values")

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        try:
            with open(csv_file, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    value, created = Value.objects.get_or_create(
                        name=row['name'],
                        slug=row['slug'],
                        defaults={
                            'description': row['description']
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Created value: {value.name}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Skipped existing value: {value.name}"))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
