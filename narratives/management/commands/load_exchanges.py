"""
Load crypto exchanges (CEX and DEX) as Topics from CSV.

CSV columns: name, exchange_type (CEX|DEX), chain (optional), keywords (optional),
source (optional), country (optional), region (optional).
- source: data source (e.g. CoinMarketCap, CoinGecko); stored in metadata and linked as related Topic.
- country / region: must match Topic names from load_geo_topics (COUNTRY / Region types).
Before linking to countries/regions, load_geo_topics is run so they exist.
"""
import csv
import os
from django.core.management import call_command
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType


# Default path relative to project root (prophet_be)
DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "csv",
    "crypto_exchanges.csv",
)

# Exchange names that must not be used as strong keyword (rely on domain/slug only).
AMBIGUOUS_EXCHANGE_NAMES = frozenset({
    "Gate", "OKX", "Bit", "Coin", "Max", "One", "Hot", "Key", "Orange", "X",
    "Fluid", "Native", "Phoenix", "Aster", "Manifest", "Project X", "ChangeNOW",
})
# Keywords that are too common and must not be added (avoid false positives).
COMMON_KEYWORD_SKIP = frozenset({
    "gate", "ok", "bit", "coin", "one", "hot", "key", "max", "x", "orange",
    "fluid", "native", "dex", "cex", "exchange",
})


class Command(BaseCommand):
    help = "Load CEX/DEX exchanges from CSV; ensure countries/regions and data sources exist; link them."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            type=str,
            default=DEFAULT_CSV,
            help=f"Path to CSV (default: {DEFAULT_CSV})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created/updated",
        )
        parser.add_argument(
            "--no-geo",
            action="store_true",
            help="Do not run load_geo_topics (use if countries/regions already loaded)",
        )

    def _get_or_create_exchange_type(self, name: str, slug: str, description: str) -> TopicType:
        """Resolve TopicType by name first, then by slug; create with given slug if missing."""
        tt = TopicType.objects.filter(name=name).first()
        if tt:
            return tt
        tt = TopicType.objects.filter(slug=slug).first()
        if tt:
            return tt
        return TopicType.objects.create(name=name, slug=slug, description=description)

    def _ensure_geo_topics(self, dry_run: bool) -> None:
        """Load countries and regions so we can link exchanges to them."""
        if dry_run:
            return
        call_command("load_geo_topics")

    def _ensure_data_source_topics(self, dry_run: bool):
        """Get or create TopicType 'Data source' and Topics CoinMarketCap, CoinGecko. Return dict name -> Topic."""
        data_source_type = TopicType.objects.filter(name="Data source").first()
        if not data_source_type:
            data_source_type = TopicType.objects.filter(slug="data-source").first()
        if not data_source_type:
            data_source_type = TopicType.objects.create(
                name="Data source",
                slug="data-source",
                description="Source of data (e.g. exchange list).",
            )
        out = {}
        for label in ("CoinMarketCap", "CoinGecko"):
            topic, _ = Topic.objects.get_or_create(
                name=label,
                defaults={"topic_type": data_source_type, "keywords": [label.lower()]},
            )
            out[label] = topic
        return out

    def _resolve_country_topic(self, country_name: str):
        """Return Topic with topic_type COUNTRY and name=country_name, or None."""
        if not country_name:
            return None
        country_type = TopicType.objects.filter(name="COUNTRY").first()
        if not country_type:
            return None
        return Topic.objects.filter(topic_type=country_type, name=country_name.strip()).first()

    def _resolve_region_topic(self, region_name: str):
        """Return Topic with topic_type Region and name=region_name, or None."""
        if not region_name:
            return None
        region_type = TopicType.objects.filter(name="Region").first()
        if not region_type:
            return None
        return Topic.objects.filter(topic_type=region_type, name=region_name.strip()).first()

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]
        no_geo = options["no_geo"]

        if not no_geo:
            self._ensure_geo_topics(dry_run)
        source_topics = self._ensure_data_source_topics(dry_run) if not dry_run else {}

        cex_type = self._get_or_create_exchange_type(
            "CEX",
            "cex",
            "Centralized crypto exchange (custodial, order-book style).",
        )
        dex_type = self._get_or_create_exchange_type(
            "DEX",
            "dex",
            "Decentralized exchange (non-custodial, AMM or order-book on-chain).",
        )

        if not os.path.isfile(csv_path):
            self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        created_count = 0
        updated_count = 0
        skipped = 0
        links_count = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "name" not in (reader.fieldnames or []) or "exchange_type" not in (reader.fieldnames or []):
                self.stdout.write(
                    self.style.ERROR("CSV must have columns: name, exchange_type")
                )
                return
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                ex_type = (row.get("exchange_type") or "").strip().upper()
                if ex_type not in ("CEX", "DEX"):
                    self.stdout.write(self.style.WARNING(f"  Skip (invalid type '{ex_type}'): {name}"))
                    skipped += 1
                    continue
                topic_type = cex_type if ex_type == "CEX" else dex_type
                chain = (row.get("chain") or "").strip()
                keywords_raw = (row.get("keywords") or "").strip()
                keywords = [
                    k.strip() for k in keywords_raw.split(",")
                    if k.strip() and k.strip().lower() not in COMMON_KEYWORD_SKIP
                ]
                if name and name not in keywords and name not in AMBIGUOUS_EXCHANGE_NAMES:
                    keywords.insert(0, name)
                if chain and chain not in keywords:
                    keywords.append(chain)
                source_name = (row.get("source") or "").strip()
                country_name = (row.get("country") or "").strip()
                region_name = (row.get("region") or "").strip()

                if dry_run:
                    exists = Topic.objects.filter(name=name).exists()
                    self.stdout.write(
                        f"  {'(exists)' if exists else 'CREATE'}: {name} [{ex_type}]"
                        + (f" source={source_name}" if source_name else "")
                        + (f" country={country_name}" if country_name else "")
                        + (f" region={region_name}" if region_name else "")
                    )
                    if not exists:
                        created_count += 1
                    continue

                topic, created = Topic.objects.get_or_create(
                    name=name,
                    defaults={
                        "topic_type": topic_type,
                        "keywords": keywords,
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created: {name} [{ex_type}]"))
                else:
                    if topic.topic_type_id != topic_type.id:
                        topic.topic_type = topic_type
                        updated_count += 1
                    if topic.keywords != keywords:
                        topic.keywords = keywords
                        updated_count += 1
                    if updated_count:
                        topic.save()
                    else:
                        skipped += 1

                # metadata: data_source
                meta = dict(topic.metadata or {})
                if source_name and meta.get("data_source") != source_name:
                    meta["data_source"] = source_name
                    topic.metadata = meta
                    topic.save()

                # related: data source topic
                if source_name and source_name in source_topics:
                    src_topic = source_topics[source_name]
                    if src_topic and not topic.related_topics.filter(pk=src_topic.pk).exists():
                        topic.related_topics.add(src_topic)
                        links_count += 1

                # related: country, region
                country_topic = self._resolve_country_topic(country_name)
                if country_topic and not topic.related_topics.filter(pk=country_topic.pk).exists():
                    topic.related_topics.add(country_topic)
                    links_count += 1
                region_topic = self._resolve_region_topic(region_name)
                if region_topic and not topic.related_topics.filter(pk=region_topic.pk).exists():
                    topic.related_topics.add(region_topic)
                    links_count += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run: would create {created_count} topics")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created: {created_count}, updated: {updated_count}, skipped: {skipped}, links: {links_count}"
                )
            )
