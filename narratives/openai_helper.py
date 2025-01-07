import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

def generate_text_with_openai(prompt, max_tokens=150, temperature=0.7):
    """
    Query OpenAI with the latest API and return the response text.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use "gpt-3.5-turbo" if you prefer
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # Correctly extract the generated message
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"OpenAI error: {e}")
