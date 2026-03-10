import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Epoch, Topic

def migrate_epochs():
    # Define data for existing epoch topics
    epoch_data = {
        "Middle Ages": {
            "earliest_start_date": 300,  # Crisis of the Third Century
            "typical_start_date": 476,   # Fall of Western Rome
            "core_start_date": 800,      # Charlemagne / Carolingian Renaissance
            "core_end_date": 1347,       # Black Death
            "typical_end_date": 1453,    # Fall of Constantinople
            "latest_end_date": 1517      # Reformation
        },
        "Renaissance": {
            "earliest_start_date": 1300,  # Petrarch / Giotto
            "typical_start_date": 1400,  # Quattrocento
            "core_start_date": 1450,     # Printing press / Gutenberg
            "core_end_date": 1550,       # Late Renaissance / Mannerism
            "typical_end_date": 1600,    # Scientific Revolution start
            "latest_end_date": 1650      # Peace of Westphalia
        },
        "Modernity": {
            "earliest_start_date": 1450,
            "typical_start_date": 1500,
            "core_start_date": 1789,
            "core_end_date": 1973,
            "typical_end_date": None,
            "latest_end_date": None
        }
    }

    for name, dates in epoch_data.items():
        topic = Topic.objects.filter(name=name).first()
        description = topic.description if topic else ""
        
        epoch, created = Epoch.objects.update_or_create(
            name=name,
            defaults={
                "description": description,
                "topic": topic,
                **dates
            }
        )
        if created:
            print(f"Created Epoch: {name}")
        else:
            print(f"Updated Epoch: {name}")

if __name__ == "__main__":
    migrate_epochs()
