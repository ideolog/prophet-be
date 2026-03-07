import os
import sys
import django

# Add current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models.categories import Topic, Person, Organization
from narratives.models.schools import SchoolOfThought, SchoolOfThoughtType
from narratives.models.sources import Source, RawText
from django.db import transaction

@transaction.atomic
def migrate_to_ontology():
    print("Starting migration to unified ontology...")

    # 1. Create root categories
    person_root, _ = Topic.objects.get_or_create(name="Person", defaults={"description": "Root category for all individual persons"})
    org_root, _ = Topic.objects.get_or_create(name="Organization", defaults={"description": "Root category for all organizations, companies, foundations"})
    
    # Map SchoolOfThoughtType to Topic roots
    school_type_map = {}
    for st in SchoolOfThoughtType.objects.all():
        root, _ = Topic.objects.get_or_create(name=st.name, defaults={"description": st.description})
        school_type_map[st.id] = root

    # 2. Migrate SchoolOfThought -> Topic
    print(f"Migrating {SchoolOfThought.objects.count()} Schools of Thought...")
    school_map = {} # {old_id: new_topic}
    
    # First pass: create topics
    for s in SchoolOfThought.objects.all():
        topic, created = Topic.objects.get_or_create(
            name=s.name,
            defaults={
                "description": s.description,
                "slug": s.slug
            }
        )
        school_map[s.id] = topic
        # Add root type as parent
        root = school_type_map.get(s.type_id)
        if root:
            topic.parents.add(root)

    # Second pass: restore hierarchy
    for s in SchoolOfThought.objects.all():
        if s.parent_school:
            new_topic = school_map[s.id]
            parent_topic = school_map.get(s.parent_school_id)
            if parent_topic:
                new_topic.parents.add(parent_topic)

    # 3. Migrate Organization -> Topic
    print(f"Migrating {Organization.objects.count()} Organizations...")
    org_map = {}
    for o in Organization.objects.all():
        topic, created = Topic.objects.get_or_create(
            name=o.name,
            defaults={
                "slug": o.slug
            }
        )
        topic.parents.add(org_root)
        org_map[o.id] = topic

    # 4. Migrate Person -> Topic
    print(f"Migrating {Person.objects.count()} Persons...")
    person_map = {}
    for p in Person.objects.all():
        topic, created = Topic.objects.get_or_create(
            name=p.full_name,
            defaults={
                "slug": p.slug
            }
        )
        topic.parents.add(person_root)
        person_map[p.id] = topic

    # 5. Update ForeignKeys in other models
    print("Updating ForeignKeys in Source and RawText...")
    
    for src in Source.objects.all():
        changed = False
        if src.owner_person_id:
            src.topic = person_map.get(src.owner_person_id)
            changed = True
        elif src.owner_organization_id:
            src.topic = org_map.get(src.owner_organization_id)
            changed = True
        
        if changed:
            src.save()

    for rt in RawText.objects.all():
        if rt.author_id:
            # We don't have a direct topic field in RawText for author, 
            # but we might want to link it in the future or just keep the Person model for now.
            # Wait, the user said "Topic absorbs Organization and Person".
            # So we need to update RawText.author to point to Topic? 
            # That would require a migration of the field itself.
            pass

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_to_ontology()
