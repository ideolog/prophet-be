"""
Migrate threat "leaf" TopicTypes to Topics.

Currently all threat subtypes (Market Volatility, Bank Run Dynamics, etc.) were
created as TopicTypes. They should be Topics with topic_type = the PESTEL type
(Economic threat, Political threat, etc.). TopicType keeps only:
  - Threat (root, is_swot=True)
  - Political threat, Economic threat, Social threat, Technological threat,
    Environmental threat, Legal threat (children of Threat)

Steps:
  1. Find leaf TopicTypes (parent is one of the 6 PESTEL types).
  2. For any existing Topic that points to a leaf type, set topic_type to the leaf's parent (PESTEL).
  3. For each leaf type, create a Topic with that name and topic_type = leaf.parent (if not exists).
  4. Delete the leaf TopicTypes.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prophet_be.settings")
django.setup()

from narratives.models import TopicType, Topic


def run():
    threat_root = TopicType.objects.filter(name="Threat").first()
    if not threat_root:
        print("TopicType 'Threat' not found. Run add_threat_topic_types.py first or skip.")
        return

    pestel_types = list(TopicType.objects.filter(parent=threat_root))
    pestel_ids = {t.id for t in pestel_types}
    # Leaf types: parent is one of PESTEL (not Threat itself, not something else)
    leaf_types = list(
        TopicType.objects.filter(parent_id__in=pestel_ids).select_related("parent")
    )

    if not leaf_types:
        print("No leaf threat TopicTypes found. Nothing to migrate.")
        return

    print(f"Found {len(leaf_types)} leaf threat types. PESTEL types: {[t.name for t in pestel_types]}")

    # 1. Fix existing Topics that point to a leaf type -> set to PESTEL parent
    updated_topics = 0
    for topic in Topic.objects.filter(topic_type_id__in=[t.id for t in leaf_types]):
        leaf = next(lt for lt in leaf_types if lt.id == topic.topic_type_id)
        topic.topic_type = leaf.parent
        topic.save()
        updated_topics += 1
        print(f"  Topic '{topic.name}' topic_type: leaf -> {leaf.parent.name}")

    # 2. Create Topic for each leaf type (name = leaf name, topic_type = PESTEL parent)
    created = 0
    for leaf in leaf_types:
        if Topic.objects.filter(name=leaf.name).exists():
            continue
        Topic.objects.create(name=leaf.name, topic_type=leaf.parent)
        created += 1
        print(f"  Created Topic: {leaf.name} (type={leaf.parent.name})")

    # 3. Delete leaf TopicTypes
    leaf_ids = [t.id for t in leaf_types]
    deleted, _ = TopicType.objects.filter(id__in=leaf_ids).delete()
    print(f"\nUpdated {updated_topics} existing topics; created {created} topics; deleted {deleted} leaf TopicTypes.")


if __name__ == "__main__":
    run()
