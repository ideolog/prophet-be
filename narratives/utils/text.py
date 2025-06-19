import re
import unicodedata
import hashlib


def generate_fingerprint(text):
    # Normalize unicode (remove diacritics etc.)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = ''.join(c for c in text if c.isprintable() and not unicodedata.category(c).startswith('C'))

    # Lowercase
    text = text.lower()

    # Remove everything except letters and numbers
    text = re.sub(r'[^a-z0-9]', '', text)

    # Generate md5 hash
    return hashlib.md5(text.encode('utf-8')).hexdigest()

