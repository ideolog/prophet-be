import csv
from django.utils.text import slugify
from django.core.management.base import BaseCommand
from narratives.models import SchoolOfThought, SchoolOfThoughtType

class Command(BaseCommand):
    help = 'Import Schools of Thought from a CSV file'

    def add_arguments(self, parser):
        # Adding an argument to specify the CSV file
        parser.add_argument('csv_file', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        self.stdout.write(self.style.SUCCESS(f'Starting import from file: {csv_file}'))

        try:
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'Name' in row and 'Description' in row and 'Type' in row:
                        self.import_school_of_thought(row)
                    else:
                        self.stdout.write(self.style.ERROR(f"Skipping row due to missing required columns: {row}"))

            self.stdout.write(self.style.SUCCESS('Import process completed successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred: {str(e)}"))

    def import_school_of_thought(self, row):
        """Import school of thought (discipline) from CSV row."""
        try:
            # Get the existing SchoolOfThoughtType (do not create new ones)
            school_type = SchoolOfThoughtType.objects.get(name=row['Type'])

            # Generate a unique slug
            slug = slugify(row['Name'])
            if SchoolOfThought.objects.filter(slug=slug).exists():
                slug = f"{slug}-{SchoolOfThought.objects.count() + 1}"  # Ensure unique slug by appending a number

            # Create or update the SchoolOfThought
            school_of_thought, created = SchoolOfThought.objects.get_or_create(
                name=row['Name'],
                defaults={
                    'description': row['Description'],
                    'type': school_type,
                    'slug': slug
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created School of Thought: {school_of_thought.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"School of Thought already exists: {school_of_thought.name}"))

        except SchoolOfThoughtType.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Type not found: {row['Type']}. Skipping row: {row}"))
