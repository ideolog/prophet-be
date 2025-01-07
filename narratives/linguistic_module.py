import spacy
from django.core.exceptions import ValidationError
from .models import Claim

# Load spaCy model
nlp = spacy.load("en_core_web_md")

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
    Performs linguistic validation on the claim.
    1. Checks for duplicates (after preprocessing).
    2. Checks for a predicate (VERB or AUX).
    """
    normalized_claim = preprocess_claim_text(claim.text)
    current_doc = nlp(normalized_claim)

    # Rule 1: Check for duplicates
    existing_claims = Claim.objects.exclude(id=claim.id).values_list('text', flat=True)
    for existing_text in existing_claims:
        existing_normalized = preprocess_claim_text(existing_text)
        existing_doc = nlp(existing_normalized)
        similarity = current_doc.similarity(existing_doc)
        if similarity > 0.9:  # Adjust threshold as needed
            raise ValidationError(f"This claim is too similar to an existing one: '{existing_text}'. Please rephrase.")

    # Rule 2: Check for presence of a predicate (VERB or AUX)
    if not any(token.pos_ in {"VERB", "AUX"} for token in current_doc):
        raise ValidationError("Claims must contain at least one action or state (predicate). Please revise your claim.")

    return "All checks passed"
