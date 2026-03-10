import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Source

def fix_avatars():
    # Mapping of DB filenames to what's actually in public/avatars
    # We'll use the filenames from the user's public/avatars folder
    
    mapping = {
        "The Moon Show": "channels4_profile_1.jpg",
        "Ivan on Tech": "ivanontech_avatar.jpg",
        "CTO LARSSON": "ctolarsson_avatar.jpg",
        "Michael Wrubel": "551461228_17978335685864435_1990598781061640404_n.jpg",
        "Crypto Kid": "channels4_profile.jpg",
        "Crypto Rover": "channels4_profile_1_njuoU0M.jpg",
        "Lark Davis": "channels4_profile_XEbd0cS.jpg",
        "Boxmining": "boxmining.jpg",
        "CoinTelegraph": "cointelegraph.jpg",
        "Vitalik.eth": "vitalik-eth.jpg"
    }
    
    for name, filename in mapping.items():
        try:
            source = Source.objects.get(name=name)
            old_file = str(source.avatar_file)
            new_file = f"sources/avatars/{filename}"
            
            if old_file != new_file:
                source.avatar_file = new_file
                source.save()
                print(f"Updated {name}: {old_file} -> {new_file}")
            else:
                print(f"Source {name} already has correct file: {new_file}")
        except Source.DoesNotExist:
            print(f"Source not found: {name}")

if __name__ == "__main__":
    fix_avatars()
