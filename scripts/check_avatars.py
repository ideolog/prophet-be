import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Source

def check_avatars():
    sources = Source.objects.all()
    print(f"{'ID':<4} | {'Name':<25} | {'Avatar File':<50} | {'Status'}")
    print("-" * 100)
    
    for s in sources:
        status = "OK"
        if not s.avatar_file:
            status = "MISSING (No file in DB)"
        else:
            # Check if the file exists in the media folder
            file_path = os.path.join('prophet_be/media', str(s.avatar_file))
            if not os.path.exists(file_path):
                status = f"BROKEN (File not in media folder: {s.avatar_file})"
        
        print(f"{s.id:<4} | {s.name[:25]:<25} | {str(s.avatar_file or ''):<50} | {status}")

if __name__ == "__main__":
    check_avatars()
