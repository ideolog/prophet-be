import os
import django
import html

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import RawText

def fix_youtube_titles():
    # Find all RawText from youtube platform
    youtube_texts = RawText.objects.filter(source__platform='youtube')
    count = 0
    for rt in youtube_texts:
        if rt.title and '&' in rt.title:
            old_title = rt.title
            new_title = html.unescape(old_title)
            if old_title != new_title:
                rt.title = new_title
                rt.save()
                count += 1
                print(f"Fixed: {old_title} -> {new_title}")
    
    print(f"Total fixed titles: {count}")

if __name__ == "__main__":
    fix_youtube_titles()
