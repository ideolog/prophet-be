import openai
import os
import json
import re
from django.utils.text import slugify

openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_narrative_claims(text):
    """
    Uses OpenAI to extract narrative claims from input text.
    Returns a tuple: (list of extracted claims, provider, model).
    """

    provider = "OpenAI"
    model = "gpt-4o"

    system_prompt = (
        "You are a Narrative Claim Extractor.\n"
        "Your task is to analyze political speeches, government press releases, legal statements, social media posts, "
        "and public addresses by political figures, and extract a list of NARRATIVE or IDEOLOGICAL CLAIMS.\n\n"
        "🎯 Your goal is to extract the **underlying worldview, assumptions, and value-based assertions** expressed in the text.\n"
        "These are statements that reflect beliefs about how the world works, what is right or wrong, or who is to blame or praised.\n\n"
        "✅ EXTRACT claims that include:\n"
        "- 💥 Enemy accusations (e.g., 'This war was started by Russia.')\n"
        "- ⚙️ Cause-effect logic (e.g., 'The Ukrainian revolution caused Russia to defend Russian people.')\n"
        "- 🧠 Worldview formulas (e.g., 'Industrialization is the path to prosperity.')\n"
        "- 🏛️ Regime characteristics (e.g., 'Bolivia is ruled by a corrupt dictatorship.')\n"
        "- 🆚 Us-vs-them framing (e.g., 'Global elites are trying to control ordinary citizens.')\n"
        "- 🧭 Value assertions (e.g., 'Freedom of speech is under attack in the West.')\n\n"
        "🚫 DO NOT EXTRACT:\n"
        "- ✔️ Polite sentiments (e.g., 'Minnesota is a great place with great people.')\n"
        "- 📅 Factual updates (e.g., 'A law was passed yesterday.')\n"
        "- 🔮 Future intentions (e.g., 'We will defeat our enemies.')\n"
        "- 🙏 Moral platitudes (e.g., 'Violence is bad.')\n"
        "- 🤝 Praise without ideology (e.g., 'Our soldiers are brave.')\n\n"
        "✍️ Guidelines:\n"
        "- Rewrite each extracted idea as a short, **clear, independent sentence**.\n"
        "- Do not quote directly.\n"
        "- No conjunctions like 'and', 'but', or 'or'. One claim per sentence.\n"
        "- Do not include questions, commands, or future promises.\n"
        "- Avoid any claim containing words like 'will', 'shall', 'is going to', or other future tense constructions.\n"
        "- Include only claims about the present or past — or those expressing ideological beliefs, accusations, or judgments.\n\n"
        "📦 Output format:\n"
        "Return ONLY a JSON object in the following format:\n"
        "{ \"narrative_claims\": [\"Claim 1.\", \"Claim 2.\", \"Claim 3.\"] }\n"
        "Return ONLY the JSON — no extra text, explanation, or commentary."
    )

    try:
        client = openai.OpenAI(api_key=openai.api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the text:\n{text}\nPlease extract narrative claims and return them in JSON."}
            ],
            temperature=0.3,
            max_tokens=500
        )

        gpt_output = response.choices[0].message.content.strip()

        try:
            narrative_data = json.loads(gpt_output)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", gpt_output)
            if json_match:
                narrative_data = json.loads(json_match.group(0))
            else:
                print(f"❌ Failed to parse GPT output as JSON: {gpt_output}")
                return None, provider, model

        return narrative_data.get("narrative_claims", []), provider, model

    except Exception as e:
        print(f"❌ OpenAI API error in narrative extraction: {e}")
        return None, provider, model
