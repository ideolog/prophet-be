from django.core.management.base import BaseCommand
import csv
from narratives.models import Category, Epoch, CategoryType  # Replace 'narratives' with your actual app name

class Command(BaseCommand):
    help = 'Add North American countries as Categories and create corresponding Epochs'

    def handle(self, *args, **kwargs):
        csv_file_path = 'north_american_countries.csv'  # Update with your actual path

        # Get or create the CategoryType for "LOCATION" and "EVENT"
        location_type, _ = CategoryType.objects.get_or_create(name='LOCATION')
        event_type, _ = CategoryType.objects.get_or_create(name='EVENT')

        with open(csv_file_path, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row

            for row in reader:
                country_name, start_date, end_date = row

                # Ensure end_date is either valid or None
                if not end_date or end_date.strip() == "":
                    end_date = None

                try:
                    # Create the Category for the country as a location
                    country_category, _ = Category.objects.get_or_create(name=country_name, category_type=location_type)

                    # Create the Category for the country's existence as an event
                    event_category, _ = Category.objects.get_or_create(name=f"Existence of {country_name}", category_type=event_type)

                    # Add the country itself as a location for its own existence event
                    event_category.locations.add(country_category)

                    # Create the Epoch for the country's existence
                    Epoch.objects.create(
                        category=event_category,
                        start_date=start_date,
                        end_date=end_date
                    )
                    self.stdout.write(self.style.SUCCESS(f'Successfully added {country_name} and its existence event from {start_date} to {end_date}'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error adding {country_name}: {e}'))

