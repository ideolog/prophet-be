import json
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from narratives.models import SchoolOfThought, SchoolOfThoughtType

class Command(BaseCommand):
    help = "Import or update Schools of Thought from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the JSON file to import")

    def handle(self, *args, **kwargs):
        json_file = kwargs["json_file"]
        self.stdout.write(self.style.SUCCESS(f"Starting import from file: {json_file}"))

        try:
            with open(json_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not read JSON: {e}"))
            return

        for entry in data:
            try:
                self.import_or_update_school(entry)
            except Exception as e:
                # We log any unexpected error but do NOT raise it, so the loop continues
                self.stdout.write(self.style.ERROR(f"Error processing entry {entry}: {e}"))

        self.stdout.write(self.style.SUCCESS("Import process completed!"))

    def import_or_update_school(self, entry):
        """
        Import or update a SchoolOfThought from a JSON entry.
        We'll match existing records by 'name', and then update:
          - description
          - type
          - parent_school
          - slug (ensuring uniqueness)
        """
        # Validate required keys
        required = ["name", "description", "type"]
        if not all(k in entry for k in required):
            raise ValueError(f"Entry missing one of required keys {required}: {entry}")

        name = entry["name"].strip()
        description = entry["description"].strip()
        type_id = entry["type"]
        parent_id = entry.get("parent_school")  # might be None
        # We'll try to respect the JSON 'slug' if present; if missing, we generate from name
        proposed_slug = entry.get("slug") or slugify(name)

        # 1) Get or create the SchoolOfThought by name
        try:
            school_type = SchoolOfThoughtType.objects.get(pk=type_id)
        except SchoolOfThoughtType.DoesNotExist:
            raise ValueError(f"SchoolOfThoughtType with PK={type_id} not found for entry {name}")

        school, created = SchoolOfThought.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "type": school_type,
                "slug": "TEMP_PLACEHOLDER",  # We'll fix slug below
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created new SchoolOfThought: {name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Found existing SchoolOfThought: {name}, updating fields..."))

        # 2) Update fields
        # Description and type are always overwritten with new data if different
        school.description = description
        school.type = school_type

        # 3) Handle parent school (if provided)
        if parent_id is not None:
            try:
                parent_school = SchoolOfThought.objects.get(pk=parent_id)
            except SchoolOfThought.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"Parent SchoolOfThought with PK={parent_id} not found; skipping parent for {name}"
                ))
                parent_school = None
        else:
            parent_school = None

        school.parent_school = parent_school

        # 4) Ensure slug is unique. If it's taken by *another* record, we generate a new one.
        unique_slug = self.make_slug_unique(proposed_slug, school)

        school.slug = unique_slug

        # 5) Try saving changes, handling IntegrityError if something else collides
        try:
            with transaction.atomic():
                school.save()
        except IntegrityError as e:
            raise ValueError(f"Failed saving {name}. Possibly another slug collision? {e}")

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} SchoolOfThought: {school.name} (slug={school.slug})"
        ))

    def make_slug_unique(self, base_slug, school_instance):
        """
        If 'base_slug' is already used by a DIFFERENT SchoolOfThought, generate a new one.
        Otherwise, return 'base_slug' as-is.
        """
        slug_candidate = base_slug
        counter = 1

        # We'll keep trying new slug variants until we find a free one or discover
        # it belongs to *this same record*
        while True:
            conflict = SchoolOfThought.objects.filter(slug=slug_candidate).exclude(pk=school_instance.pk).first()
            if not conflict:
                # It's free or used by the same record
                return slug_candidate
            # Otherwise, create a new variant
            slug_candidate = f"{base_slug}-{counter}-{get_random_string(3)}"
            counter += 1
