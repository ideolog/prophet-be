"""
Load all value topics from data/csv/*value*.csv into Topics with topic_type=Value.

Finds every CSV in data/csv whose filename contains "value", reads name/slug/description
(any column order, extra columns like category/religion ignored), deduplicates by name,
then creates or updates Topics with topic_type = TopicType "Value".
"""
import os
import csv
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prophet_be.settings")
django.setup()

from narratives.models import Topic, TopicType

DATA_CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "csv")


def main():
    csv_dir = os.path.abspath(DATA_CSV_DIR)
    if not os.path.isdir(csv_dir):
        print(f"Directory not found: {csv_dir}")
        return

    value_files = sorted(
        f for f in os.listdir(csv_dir)
        if "value" in f.lower() and f.endswith(".csv")
    )
    if not value_files:
        print(f"No *value*.csv files in {csv_dir}")
        return

    print(f"Found {len(value_files)} value CSV(s): {value_files}")

    value_type, _ = TopicType.objects.get_or_create(
        name="Value",
        defaults={"description": "Human and systemic values, principles, ethics"},
    )

    # name -> {slug, description}; first file wins for slug/description
    by_name = {}
    for filename in value_files:
        path = os.path.join(csv_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                slug = (row.get("slug") or "").strip() or None
                desc = (row.get("description") or "").strip() or None
                if name not in by_name:
                    by_name[name] = {"slug": slug, "description": desc}
                elif by_name[name]["description"] is None and desc:
                    by_name[name]["description"] = desc

    print(f"Total unique names: {len(by_name)}")

    created = 0
    updated = 0
    skipped = 0
    for name, data in sorted(by_name.items()):
        topic, created_flag = Topic.objects.get_or_create(
            name=name,
            defaults={
                "topic_type": value_type,
                "description": data["description"],
            },
        )
        if created_flag:
            if data["slug"]:
                topic.slug = data["slug"]
                topic.save()
            created += 1
            print(f"  + {name}")
        else:
            if topic.topic_type_id != value_type.id:
                topic.topic_type = value_type
                if data["description"] and not topic.description:
                    topic.description = data["description"]
                topic.save()
                updated += 1
                print(f"  ~ {name} (set type Value)")
            else:
                skipped += 1

    print(f"\nDone. Created: {created}, updated type: {updated}, skipped: {skipped}")


if __name__ == "__main__":
    main()
