# narratives/utils/school_of_thought.py
"""Ensure topics used as School of thought have topic_type = 'School of thought'."""

from narratives.models import Topic, TopicType


def get_school_of_thought_type():
    """Return TopicType named 'School of thought' or None if not found."""
    return TopicType.objects.filter(name__iexact="School of thought").first()


def ensure_school_topics_have_type(school_topic_ids):
    """
    For each topic in school_topic_ids, if its topic_type is not 'School of thought', set it.
    Call this after setting schools_of_thought on a topic (so the referenced topics get the type).
    """
    sot_type = get_school_of_thought_type()
    if not sot_type:
        return
    for topic in Topic.objects.filter(id__in=school_topic_ids):
        if topic.topic_type_id != sot_type.id:
            topic.topic_type = sot_type
            topic.save(update_fields=["topic_type_id"])
