# narratives/management/commands/load_geo_topics.py
"""
Load countries (from ISO 3166-1) and geographic regions as Topics.
- Countries: common names (no commas, no leading 'The'); type COUNTRY; keywords = ISO2, ISO3, alternates.
- Regions: e.g. Middle East, Far East; type Region.
Name is the most common / Wikipedia-style form (e.g. North Korea not Korea, Democratic People's Republic of).
"""
import re
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType

# ISO official name -> common name (Wikipedia-style, no commas, no "The")
COMMON_NAME_OVERRIDES = {
    "Korea, Democratic People's Republic of": "North Korea",
    "Korea, Republic of": "South Korea",
    "Iran, Islamic Republic of": "Iran",
    "Lao People's Democratic Republic": "Laos",
    "Brunei Darussalam": "Brunei",
    "Bolivia, Plurinational State of": "Bolivia",
    "Venezuela, Bolivian Republic of": "Venezuela",
    "Tanzania, United Republic of": "Tanzania",
    "Syrian Arab Republic": "Syria",
    "Russian Federation": "Russia",
    "Republic of Moldova": "Moldova",
    "Viet Nam": "Vietnam",
    "Czechia": "Czech Republic",
    "Turkiye": "Turkey",
    "Hong Kong": "Hong Kong",
    "Macao": "Macau",
    "Taiwan, Province of China": "Taiwan",
    "Palestine, State of": "Palestine",
    "Congo": "Republic of the Congo",
    "Congo, Democratic Republic of the": "Democratic Republic of the Congo",
    "Congo, The Democratic Republic of the": "Democratic Republic of the Congo",
    "Gambia": "The Gambia",  # We strip "The" in normalise_name, so store as Gambia
    "Bahamas": "Bahamas",
    "Philippines": "Philippines",
    "Netherlands": "Netherlands",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United States of America": "United States",
    "United Arab Emirates": "United Arab Emirates",
    "Holy See": "Vatican City",
    "Micronesia, Federated States of": "Micronesia",
    "Saint Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "Saint Lucia": "Saint Lucia",
    "Saint Kitts and Nevis": "Saint Kitts and Nevis",
    "Antigua and Barbuda": "Antigua and Barbuda",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Sao Tome and Principe": "Sao Tome and Principe",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "North Macedonia": "North Macedonia",
    "Eswatini": "Eswatini",
    "Timor-Leste": "East Timor",
    "Côte d'Ivoire": "Ivory Coast",
}
# Strip "The" from display name (store without The)
STRIP_THE = {"The Gambia": "Gambia", "The Bahamas": "Bahamas"}


def _add_the_form_to_keywords(display_name: str, keywords: list) -> list:
    """If we stripped 'The', add 'The X' to keywords so both forms match."""
    for the_form, short in STRIP_THE.items():
        if short == display_name and the_form not in keywords:
            return keywords + [the_form]
    return keywords

# ISO 3166-1 alpha_2 codes that are common English words or too ambiguous as standalone keywords.
# We still use alpha_3 and full/official names. Reduces false positives (e.g. "IN" matching " in ").
COUNTRY_ALPHA2_SKIP = frozenset({
    "IN", "US", "AS", "NO", "TO", "TV", "AI", "MY", "BY", "IT", "IS", "AT", "SO", "DO",
    "ME", "NE", "OR", "BE", "GO", "WE", "ON", "AN", "HE", "LA", "AD", "IE", "SE", "EE",
})

REGIONS = [
    {"name": "Middle East", "keywords": ["Middle East", "MENA"]},
    {"name": "Far East", "keywords": ["Far East", "East Asia"]},
    {"name": "Southeast Asia", "keywords": ["Southeast Asia", "SE Asia"]},
    {"name": "South Asia", "keywords": ["South Asia", "Indian subcontinent"]},
    {"name": "Central Asia", "keywords": ["Central Asia"]},
    {"name": "Eastern Europe", "keywords": ["Eastern Europe"]},
    {"name": "Western Europe", "keywords": ["Western Europe"]},
    {"name": "North Africa", "keywords": ["North Africa"]},
    {"name": "Sub-Saharan Africa", "keywords": ["Sub-Saharan Africa", "SSA"]},
    {"name": "Latin America", "keywords": ["Latin America", "LATAM"]},
    {"name": "Caribbean", "keywords": ["Caribbean"]},
    {"name": "North America", "keywords": ["North America"]},
    {"name": "Oceania", "keywords": ["Oceania", "Pacific Islands"]},
    {"name": "Balkans", "keywords": ["Balkans", "Balkan region"]},
    {"name": "Scandinavia", "keywords": ["Scandinavia", "Nordic"]},
    {"name": "Caucasus", "keywords": ["Caucasus"]},
]


def normalise_name(s: str) -> str:
    """Remove commas from name; strip leading 'The '."""
    if not s:
        return s
    s = s.strip()
    # Remove leading "The "
    if s.startswith("The "):
        s = s[4:].strip()
    # Replace commas with " and " or remove (e.g. "Korea, Republic of" -> we use overrides)
    s = re.sub(r"\s*,\s*", " ", s)
    return s.strip()


def slugify_name(s: str) -> str:
    """Simple slug for Wikipedia URL path."""
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "_", s.strip())
    return s[:100] if s else ""


class Command(BaseCommand):
    help = "Load countries (ISO 3166-1) and geographic regions as Topics with type COUNTRY / Region"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created",
        )
        parser.add_argument(
            "--countries-only",
            action="store_true",
            help="Load only countries",
        )
        parser.add_argument(
            "--regions-only",
            action="store_true",
            help="Load only regions",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        countries_only = options["countries_only"]
        regions_only = options["regions_only"]

        country_type = TopicType.objects.filter(name="COUNTRY").first()
        if not country_type:
            country_type = TopicType.objects.filter(slug="country").first()
        if not country_type:
            country_type = TopicType.objects.create(
                name="COUNTRY",
                slug="iso-country",
                description="Sovereign state or country (ISO 3166-1). Use common English name, no commas, no leading The.",
            )
        region_type = TopicType.objects.filter(name="Region").first()
        if not region_type:
            region_type = TopicType.objects.filter(slug="region").first()
        if not region_type:
            region_type = TopicType.objects.create(
                name="Region",
                slug="geo-region",
                description="Geographic region (e.g. Middle East, Far East).",
            )
        if not TopicType.objects.filter(name="State/Province").exists() and not TopicType.objects.filter(slug="state-province").exists():
            TopicType.objects.create(name="State/Province", slug="state-province", description="State, province, or first-level administrative region within a country.")
        if not TopicType.objects.filter(name="City").exists() and not TopicType.objects.filter(slug="city").exists():
            TopicType.objects.create(name="City", slug="city", description="City or town. When suggesting, always provide context_country (and context_region or state if needed) for disambiguation.")
        if not regions_only:
            self._load_countries(country_type, dry_run)
        if not countries_only:
            self._load_regions(region_type, dry_run)

    def _load_countries(self, country_type, dry_run):
        try:
            import pycountry
        except ImportError:
            self.stdout.write(self.style.ERROR("Install pycountry: pip install pycountry"))
            return

        created = 0
        updated = 0
        for c in pycountry.countries:
            official = c.name
            common = COMMON_NAME_OVERRIDES.get(official)
            if common is None:
                common = normalise_name(official)
            if not common:
                continue
            # Final display name: no "The"
            display_name = STRIP_THE.get(common, common)
            keywords = [c.alpha_3]
            if c.alpha_2 not in COUNTRY_ALPHA2_SKIP:
                keywords.append(c.alpha_2)
            keywords = _add_the_form_to_keywords(display_name, keywords)
            if getattr(c, "common_name", None) and c.common_name != display_name:
                keywords.append(c.common_name)
            if official != display_name and official not in keywords:
                keywords.append(official)
            # Wikipedia URL
            wiki_slug = slugify_name(display_name)
            wikipedia_url = f"https://en.wikipedia.org/wiki/{wiki_slug}" if wiki_slug else None
            alternative_name = official if official != display_name else None

            if dry_run:
                self.stdout.write(f"  {display_name} | alt={alternative_name} | kw={keywords[:4]}")
                created += 1
                continue

            topic, created_t = Topic.objects.get_or_create(
                name=display_name,
                defaults={
                    "topic_type": country_type,
                    "alternative_name": alternative_name,
                    "keywords": keywords,
                    "wikipedia_url": wikipedia_url,
                },
            )
            if created_t:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {display_name}"))
            else:
                if topic.topic_type_id != country_type.id:
                    topic.topic_type = country_type
                    topic.save()
                    updated += 1
                if topic.alternative_name != alternative_name and alternative_name:
                    topic.alternative_name = alternative_name
                    topic.save()
                if topic.keywords != keywords:
                    topic.keywords = keywords
                    topic.save()

        self.stdout.write(self.style.SUCCESS(f"Countries: created={created}, updated={updated}"))

    def _load_regions(self, region_type, dry_run):
        created = 0
        for r in REGIONS:
            name = r["name"]
            keywords = r.get("keywords", [name])
            if name not in keywords:
                keywords = [name] + list(keywords)
            wiki_slug = slugify_name(name)
            wikipedia_url = f"https://en.wikipedia.org/wiki/{wiki_slug}" if wiki_slug else None

            if dry_run:
                self.stdout.write(f"  Region: {name} | kw={keywords}")
                created += 1
                continue

            topic, created_t = Topic.objects.get_or_create(
                name=name,
                defaults={
                    "topic_type": region_type,
                    "keywords": keywords,
                    "wikipedia_url": wikipedia_url,
                },
            )
            if created_t:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Created region: {name}"))
            else:
                if topic.topic_type_id != region_type.id:
                    topic.topic_type = region_type
                    topic.save()
                existing = list(topic.keywords or [])
                for kw in keywords:
                    if kw not in existing:
                        existing.append(kw)
                topic.keywords = existing
                topic.wikipedia_url = topic.wikipedia_url or wikipedia_url
                topic.save()

        self.stdout.write(self.style.SUCCESS(f"Regions: created={created}"))
