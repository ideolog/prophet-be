import os
import sys
import django

# Add current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models.categories import Topic
from narratives.models.values import Value
from django.db import transaction

@transaction.atomic
def migrate_values_to_ontology():
    print("Starting migration of Values to unified ontology...")

    # 1. Create root category for Values
    value_root, _ = Topic.objects.get_or_create(
        name="Value", 
        defaults={"description": "Root category for all human and systemic values, principles, and ethics"}
    )
    
    # 2. Migrate Value -> Topic
    values_count = Value.objects.count()
    print(f"Migrating {values_count} Values...")
    
    for v in Value.objects.all():
        topic, created = Topic.objects.get_or_create(
            name=v.name,
            defaults={
                "description": v.description,
                "slug": v.slug
            }
        )
        # If topic existed but description was empty, update it
        if not created and not topic.description and v.description:
            topic.description = v.description
            topic.save()
            
        # Add root "Value" as parent
        topic.parents.add(value_root)
        print(f"  - Migrated: {v.name}")

    print("Migration of Values completed successfully!")

if __name__ == "__main__":
    migrate_values_to_ontology()
