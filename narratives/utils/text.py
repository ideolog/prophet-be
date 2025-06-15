import unicodedata
import hashlib
import re

def generate_fingerprint(text):
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))  # remove diacritics
    text = ''.join(c for c in text if c.isprintable() and not unicodedata.category(c).startswith('C'))  # remove control chars
    text = re.sub(r'\W+', '', text.lower())  # strip punctuation, lowercase
    return hashlib.md5(text.encode('utf-8')).hexdigest()
