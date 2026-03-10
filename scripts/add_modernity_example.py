import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Epoch

def add_modernity():
    modernity, created = Epoch.objects.get_or_create(
        name="Modernity",
        defaults={
            "description": "The historical period characterized by the rise of industrialization, capitalism, secularism, and the nation-state.",
            "notes_on_periodization": "Periodization of modernity is highly debated. We use 1450 (printing press) as earliest, 1500 (discovery of Americas) as typical, and 1789 (French Revolution) as the start of the core phase. 1973 (oil crisis/post-modern turn) marks the end of the core phase.",
            "earliest_start_date": 1450,
            "typical_start_date": 1500,
            "core_start_date": 1789,
            "core_end_date": 1973,
            "typical_end_date": None,
            "latest_end_date": None
        }
    )
    if created:
        print("Modernity epoch created successfully.")
    else:
        print("Modernity epoch already exists.")

if __name__ == "__main__":
    add_modernity()
