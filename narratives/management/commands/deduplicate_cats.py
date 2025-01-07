from django.core.management.base import BaseCommand
from narratives.models import Category
from collections import defaultdict

class Command(BaseCommand):
    help = 'Deduplicate categories with the same name'

    def handle(self, *args, **kwargs):
        categories_by_name = defaultdict(list)

        # Group categories by name
        for category in Category.objects.all():
            categories_by_name[category.name].append(category)

        # Iterate over the grouped categories and remove duplicates
        for name, categories in categories_by_name.items():
            if len(categories) > 1:
                # Keep the first one, remove the rest
                primary_category = categories[0]
                duplicates = categories[1:]
                for duplicate in duplicates:
                    # Transfer relationships before deleting
                    duplicate.locations.clear()
                    duplicate.persons.clear()
                    duplicate.delete()

                self.stdout.write(self.style.SUCCESS(f"Deduplicated {name}, kept {primary_category}"))

