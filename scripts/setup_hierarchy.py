from narratives.models import Topic

def setup_topic_hierarchy():
    # Define the hierarchy structure
    hierarchy = {
        "Infrastructure": {
            "Layer 1": {
                "Bitcoin Ecosystem": {
                    "keywords": ["Bitcoin", "BTC"],
                    "children": ["BRC-20", "Runes", "Ordinals", "Stacks"]
                },
                "Ethereum Ecosystem": {
                    "keywords": ["Ethereum", "ETH"],
                    "children": ["EVM", "Liquid Staking", "Restaking"]
                },
                "Solana Ecosystem": {
                    "keywords": ["Solana", "SOL"],
                    "children": ["Solana DeFi", "Solana NFTs"]
                },
                "Cosmos Ecosystem": {
                    "keywords": ["Cosmos", "ATOM"],
                    "children": ["IBC", "Appchains"]
                },
            },
            "Layer 2": {
                "Rollups": ["Optimistic Rollups", "ZK Rollups"],
                "Sidechains": [],
                "State Channels": [],
            },
            "Layer 3": [],
            "Data Availability": ["Modular Blockchains", "Celestia Ecosystem", "Avail Ecosystem"],
            "Interoperability": ["Cross-chain Bridges", "Omnichain Protocols"],
            "Wallets & UX": ["Account Abstraction", "Smart Accounts", "Social Recovery"],
        },
        "DeFi": {
            "Lending & Borrowing": ["Isolated Lending", "Undercollateralized Lending"],
            "DEXs": ["AMM", "Orderbook DEX", "Aggregators"],
            "Derivatives": ["Perpetual Swaps", "Options", "Synthetic Assets"],
            "Yield Farming": ["Liquid Staking", "Liquid Restaking"],
            "Stablecoins": ["Algorithmic Stablecoins", "Fiat-backed Stablecoins", "CDP Stablecoins"],
            "Real World Assets (RWA)": ["Tokenized Real Estate", "Tokenized Treasury Bills"],
        },
        "Consumer Apps": {
            "Gaming (GameFi)": ["Play-to-Earn", "Fully On-chain Games"],
            "Social (SocialFi)": ["DeSoc", "Creator Tokens"],
            "NFTs": ["NFT Marketplaces", "Generative Art", "PFP Collections"],
            "Metaverse": ["Virtual Land", "Digital Identity"],
        },
        "Security & Privacy": {
            "Privacy Protocols": {
                "Zero Knowledge Proofs (ZKP)": ["zero-knowledge proof", "zkp", "zero knowledge proof", "zeroKnowledge proof", "zk-proof", "snark", "stark", "succinct non-interactive argument of knowledge"],
                "Mixers": ["tornado cash", "coinjoin", "mixer"],
                "Private Transactions": ["stealth address", "shielded transaction", "zcash", "monero"]
            },
            "Auditing & Insurance": ["Smart Contract Audits", "DeFi Insurance"],
            "MEV": ["MEV Protection", "Searchers", "Flashbots"],
        },
        "Governance & DAO": {
            "DAO Tooling": ["Voting Platforms", "Treasury Management"],
            "Governance Tokens": ["Voter Extraction", "Liquid Governance"],
        },
        "Standards": [
            "ERC-20", "ERC-721", "ERC-1155", "ERC-4626", "ERC-4337", 
            "ERC-6551", "ERC-7579", "ERC-2612", "ERC-2771", "ERC-3643", 
            "ERC-1400", "ERC-1271", "ERC-5219", "ERC-7540", "ERC-7786", 
            "ERC-8004", "ERC-55", "ERC-191", "ERC-712"
        ],
        "Emerging Tech": {
            "AI & Crypto": ["Decentralized Compute", "AI Agents", "DePIN"],
            "DePIN": ["Decentralized Storage", "Decentralized Wireless (DeWi)", "Decentralized GPU Networks"],
        }
    }

    def process_node(node_name, data, parent_obj=None):
        # Get or create the topic
        topic, _ = Topic.objects.get_or_create(name=node_name)
        
        # Add parent if provided
        if parent_obj:
            topic.parents.add(parent_obj)
            print(f"Added parent {parent_obj.name} to {topic.name}")
        
        # Handle different data formats
        keywords = []
        children = None

        if isinstance(data, dict):
            if "keywords" in data or "children" in data:
                keywords = data.get("keywords", [])
                children = data.get("children", [])
            else:
                # It's a nested hierarchy dict
                children = data
        elif isinstance(data, list):
            # It's a list of children or keywords
            if all(isinstance(item, str) for item in data) and node_name in [
                "Zero Knowledge Proofs (ZKP)", "Mixers", "Private Transactions"
            ]:
                keywords = data
            else:
                children = data

        # Update keywords if any
        if keywords:
            topic.keywords = list(set(topic.keywords + keywords))
            topic.save()
            print(f"Updated keywords for {topic.name}: {topic.keywords}")

        # Process children
        if isinstance(children, dict):
            for child_name, child_data in children.items():
                process_node(child_name, child_data, topic)
        elif isinstance(children, list):
            for child_name in children:
                if isinstance(child_name, str):
                    child_topic, _ = Topic.objects.get_or_create(name=child_name)
                    child_topic.parents.add(topic)
                    print(f"Added parent {topic.name} to {child_topic.name}")
                else:
                    # Handle nested objects if any
                    pass

    # Start processing from the root of our defined hierarchy
    for root_name, data in hierarchy.items():
        process_node(root_name, data)

    print("Hierarchy setup complete.")

if __name__ == "__main__":
    setup_topic_hierarchy()
