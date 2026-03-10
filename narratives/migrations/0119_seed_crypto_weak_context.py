# narratives/migrations/0119_seed_crypto_weak_context.py
from django.db import migrations


def create_crypto_weak_context(apps, schema_editor):
    ContextSet = apps.get_model("narratives", "ContextSet")
    if ContextSet.objects.filter(slug="CRYPTO_WEAK_CONTEXT").exists():
        return
    ContextSet.objects.create(
        slug="CRYPTO_WEAK_CONTEXT",
        name="Crypto weak keyword context",
        words=[
            "crypto", "token", "marketcap", "price", "coin", "trading", "asset",
            "volume", "exchange", "wallet", "supply", "blockchain", "defi", "eth",
            "btc", "market", "cap", "ticker",
        ],
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("narratives", "0118_contextset"),
    ]

    operations = [
        migrations.RunPython(create_crypto_weak_context, noop),
    ]
