import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Topic, TopicType

def fix_types():
    # 1. Assign 'Blockchain network' type
    network_type = TopicType.objects.filter(name='Blockchain network').first()
    if network_type:
        count = Topic.objects.filter(name__icontains='network').update(topic_type=network_type)
        print(f"Updated {count} topics to 'Blockchain network'")

    # 2. Assign 'Person' type
    person_type = TopicType.objects.filter(name='Person').first()
    if person_type:
        people = ['Vitalik Buterin', 'Donald Trump', 'Michael Saylor', 'Elon Musk', 'Satoshi Nakamoto']
        count = Topic.objects.filter(name__in=people).update(topic_type=person_type)
        print(f"Updated {count} topics to 'Person'")

    # 3. Assign 'Organization' type
    org_type = TopicType.objects.filter(name='Organization').first()
    if org_type:
        orgs = ['Coinbase', 'Binance', 'Kraken', 'The White House', 'SEC', 'Federal Reserve']
        count = Topic.objects.filter(name__in=orgs).update(topic_type=org_type)
        print(f"Updated {count} topics to 'Organization'")

if __name__ == "__main__":
    fix_types()
