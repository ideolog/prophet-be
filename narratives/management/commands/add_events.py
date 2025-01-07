from django.core.management.base import BaseCommand
import csv
from django.core.exceptions import ValidationError
from narratives.models import Category, Epoch, CategoryType  # Replace 'narratives' with your app name


class Command(BaseCommand):
    help = 'Add U.S. Presidents and their terms as Events and create corresponding Epochs'

    def handle(self, *args, **kwargs):
        csv_file_path = 'us_presidents_terms.csv'  # Update with your actual path

        # Get or create the CategoryType for "PERSON" and "EVENT"
        person_type, _ = CategoryType.objects.get_or_create(name='PERSON')
        event_type, _ = CategoryType.objects.get_or_create(name='EVENT')

        # Get or create the location "USA"
        usa_location, _ = Category.objects.get_or_create(name='USA', category_type=person_type)

        with open(csv_file_path, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row

            for row in reader:
                president_name, start_date, end_date = row

                # Ensure end_date is either valid or None
                if not end_date or end_date.strip() == "":
                    end_date = None

                try:
                    # Create the Category for the president
                    president_category, _ = Category.objects.get_or_create(name=president_name, category_type=person_type)

                    # Create the Category for the presidential term as an event
                    event_category, _ = Category.objects.get_or_create(name=f"{president_name} Presidential Term", category_type=event_type)

                    # Add USA as the location for the event
                    event_category.locations.add(usa_location)

                    # Associate the president (person) with the event
                    event_category.persons.add(president_category)

                    # Create the Epoch for the presidential term
                    Epoch.objects.create(
                        category=event_category,
                        start_date=start_date,
                        end_date=end_date  # This will now be None if no valid end date is provided
                    )
                    self.stdout.write(self.style.SUCCESS(f'Successfully added {president_name} Presidential Term from {start_date} to {end_date}'))

                except ValidationError as e:
                    self.stdout.write(self.style.ERROR(f'Error adding {president_name}: {e}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Unexpected error adding {president_name}: {e}'))
