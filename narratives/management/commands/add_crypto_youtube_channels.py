# narratives/management/commands/add_crypto_youtube_channels.py
"""Add crypto YouTube channels from data/crypto_youtube_channels.txt (one URL per line)."""

import os
from django.core.management.base import BaseCommand
from django.conf import settings

from narratives.utils.youtube_add import add_youtube_channel_by_url


def get_channels_file():
    base = getattr(settings, "BASE_DIR", None) or os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    return os.path.join(base, "data", "crypto_youtube_channels.txt")


class Command(BaseCommand):
    help = "Add crypto YouTube channels from data/crypto_youtube_channels.txt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to text file with one channel URL per line (default: data/crypto_youtube_channels.txt)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print URLs that would be added, do not call API",
        )

    def handle(self, *args, **options):
        path = options.get("file") or get_channels_file()
        dry_run = options.get("dry_run", False)

        if not os.path.isfile(path):
            self.stdout.write(self.style.ERROR(f"File not found: {path}"))
            return

        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

        urls = [ln for ln in lines if ln.startswith("http")]
        if not urls:
            self.stdout.write(self.style.WARNING("No URLs found in file."))
            return

        if dry_run:
            for u in urls:
                self.stdout.write(u)
            self.stdout.write(self.style.SUCCESS(f"Dry run: {len(urls)} URLs would be processed."))
            return

        if not getattr(settings, "YOUTUBE_API_KEY", None):
            self.stdout.write(self.style.ERROR("YOUTUBE_API_KEY not set in settings."))
            return

        added = 0
        for url in urls:
            try:
                source, created = add_youtube_channel_by_url(url)
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Added: {source.name} ({url})"))
                    added += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Already exists: {source.name}"))
            except ValueError as e:
                self.stdout.write(self.style.WARNING(f"Skip {url}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error {url}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Added {added} channels."))
