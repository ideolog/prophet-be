from django.core.exceptions import ValidationError
from .models import Claim

def preprocess_claim_text(text):
    """
    Preprocesses claim text by:
    1. Lowercasing
    2. Removing stop words and extra spaces
    3. Removing repeated words
    """
    doc = nlp(text.lower())
    words = []
    for token in doc:
        if not token.is_stop and token.is_alpha:  # Remove stop words and keep only alphabetic tokens
            words.append(token.text)

    # Remove repeated words
    cleaned_text = " ".join(sorted(set(words), key=words.index))
    return cleaned_text

def check_claim_validity(claim):
    """
    Placeholder function since backend checks are disabled.
    """
    pass

