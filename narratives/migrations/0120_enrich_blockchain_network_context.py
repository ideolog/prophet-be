# narratives/migrations/0120_enrich_blockchain_network_context.py
from django.db import migrations


EXTRA_WORDS = [
    "network", "blockchain", "layer", "mainnet", "L1", "L2", "protocol", "chain",
    "consensus", "validator", "node", "smart contract", "dapp", "evm", "bridge",
    "rollup", "sidechain",
]


def enrich_blockchain_network(apps, schema_editor):
    ContextSet = apps.get_model("narratives", "ContextSet")
    cs = ContextSet.objects.filter(slug="BLOCKCHAIN_NETWORK").first()
    if not cs:
        return
    existing = list(cs.words or [])
    seen = {w.strip().lower() for w in existing if (w or "").strip()}
    for w in EXTRA_WORDS:
        w = (w or "").strip()
        if w and w.lower() not in seen:
            existing.append(w)
            seen.add(w.lower())
    cs.words = existing
    cs.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("narratives", "0119_seed_crypto_weak_context"),
    ]

    operations = [
        migrations.RunPython(enrich_blockchain_network, noop),
    ]
