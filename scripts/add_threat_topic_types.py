"""
Adds the full hierarchy of threat TopicTypes:
  Threat (is_swot=True)
    ├── Political threat
    │     ├── Crypto Prohibition, Capital Controls, ...
    ├── Economic threat
    │     ├── Market Volatility, Liquidity Risk, ...
    ├── Social threat
    ├── Technological threat
    ├── Environmental threat
    └── Legal threat
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import TopicType

THREAT_TAXONOMY = {
    "Political threat": [
        "Crypto Prohibition",
        "Capital Controls",
        "Financial Surveillance",
        "Financial Censorship",
        "Monetary Sovereignty",
        "Central Bank Digital Currency",
        "Sanctions Regime",
        "Geopolitical Conflict",
        "Policy Uncertainty",
        "Regulatory Capture",
        "State Hostility to Decentralization",
        "Digital Authoritarianism",
    ],
    "Economic threat": [
        "Market Volatility",
        "Liquidity Risk",
        "Counterparty Risk",
        "Stablecoin Instability",
        "Exchange Insolvency",
        "Credit Contraction",
        "Leverage Cascade",
        "Bank Run Dynamics",
        "Speculative Bubble",
        "Market Manipulation",
        "Wealth Concentration",
        "Token Inflation",
        "Token Deflation",
        "Reflexivity",
        "Network Fee Shock",
        "Incentive Misalignment",
        "Unsustainable Tokenomics",
    ],
    "Social threat": [
        "Moral Panic",
        "Public Distrust",
        "Herd Behavior",
        "Fear of Missing Out",
        "Panic Buying",
        "Panic Selling",
        "Scam Culture",
        "Community Fragmentation",
        "Tribalism",
        "Reputation Crisis",
        "Influencer Dependence",
        "User Illiteracy",
        "Adoption Resistance",
        "Narrative Manipulation",
        "Technological Elitism",
    ],
    "Technological threat": [
        "Smart Contract Vulnerability",
        "Bridge Vulnerability",
        "Oracle Manipulation",
        "Consensus Attack",
        "Majority Attack",
        "Validator Centralization",
        "Mining Centralization",
        "Client Software Failure",
        "Protocol Failure",
        "Governance Attack",
        "Sybil Attack",
        "Denial-of-Service Attack",
        "Key Management Failure",
        "Wallet Vulnerability",
        "Interoperability Failure",
        "Scalability Constraint",
        "Network Congestion",
        "Maximal Extractable Value",
        "Infrastructure Centralization",
        "Upgrade Risk",
        "Cryptographic Obsolescence",
        "Quantum Computing Threat",
    ],
    "Environmental threat": [
        "Energy Consumption",
        "Carbon Regulation",
        "Climate Policy",
        "Mining Externality",
        "Electronic Waste",
        "Water Consumption",
        "Heat Stress",
        "Flood Risk",
        "Resource Scarcity",
        "Supply Chain Disruption",
        "Geographic Concentration of Mining",
    ],
    "Legal threat": [
        "Token Classification",
        "Securities Enforcement",
        "Anti-Money Laundering Regulation",
        "Know Your Customer Regulation",
        "Privacy Coin Restriction",
        "Tax Uncertainty",
        "Retroactive Enforcement",
        "Jurisdictional Conflict",
        "Licensing Burden",
        "Developer Liability",
        "Decentralized Autonomous Organization Liability",
        "Consumer Protection Enforcement",
        "Data Protection Conflict",
        "Financial Crime Compliance",
        "Stablecoin Regulation",
        "Custody Regulation",
        "Staking Regulation",
    ],
}


def run():
    created_count = 0
    updated_count = 0

    # 1. Threat (root, is_swot=True)
    threat, c = TopicType.objects.get_or_create(name="Threat", defaults={"is_swot": True})
    if c:
        created_count += 1
        print("Created: Threat (is_swot=True)")
    elif not threat.is_swot:
        threat.is_swot = True
        threat.save()
        updated_count += 1
        print("Updated: Threat (set is_swot=True)")

    # 2. PESTEL parent types (parent = Threat)
    pestel_types = {}
    for pestel_name in THREAT_TAXONOMY.keys():
        obj, c = TopicType.objects.get_or_create(
            name=pestel_name,
            defaults={"parent": threat}
        )
        if c:
            created_count += 1
            print(f"  Created: {pestel_name}")
        elif obj.parent_id != threat.id:
            obj.parent = threat
            obj.save()
            updated_count += 1
            print(f"  Updated: {pestel_name} (set parent=Threat)")
        pestel_types[pestel_name] = obj

    # 3. Leaf types (parent = PESTEL type)
    for pestel_name, leaves in THREAT_TAXONOMY.items():
        parent = pestel_types[pestel_name]
        for leaf_name in leaves:
            obj, c = TopicType.objects.get_or_create(
                name=leaf_name,
                defaults={"parent": parent}
            )
            if c:
                created_count += 1
                print(f"    Created: {leaf_name} (under {pestel_name})")
            elif obj.parent_id != parent.id:
                obj.parent = parent
                obj.save()
                updated_count += 1
                print(f"    Updated: {leaf_name} (set parent={pestel_name})")

    total = sum(len(v) for v in THREAT_TAXONOMY.values()) + len(THREAT_TAXONOMY) + 1
    print(f"\nDone. Created: {created_count}, Updated: {updated_count}, Total types in tree: {total}")


if __name__ == "__main__":
    run()
