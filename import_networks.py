import requests
import time
from narratives.models import Topic

def import_blockchain_networks():
    # 1. Ensure base topics exist
    blockchain_parent, _ = Topic.objects.get_or_create(
        name="Blockchain",
        defaults={"description": "A distributed ledger technology."}
    )
    
    network_type, _ = Topic.objects.get_or_create(
        name="Blockchain network",
        defaults={
            "is_placeholder": True,
            "description": "Classification type for blockchain protocols and networks."
        }
    )
    
    # Also ensure 'Blockchain network' is a child of 'Blockchain'
    blockchain_parent.children.add(network_type)

    base_url = "https://api.geckoterminal.com/api/v2/networks"
    headers = {"accept": "application/json"}
    
    page = 1
    total_imported = 0
    
    print(f"Starting import from CoinGecko Terminal...")

    while True:
        try:
            print(f"Fetching page {page}...")
            response = requests.get(f"{base_url}?page={page}", headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            networks = data.get("data", [])
            if not networks:
                break
                
            for net in networks:
                attr = net.get("attributes", {})
                raw_name = attr.get("name")
                raw_id = net.get("id")
                
                if not raw_name:
                    continue
                
                # Rules:
                # Title: Name + " network"
                # Alternative: ID + " network"
                # Type: Blockchain network
                # Parents: Blockchain, Blockchain network
                # Weak Keyword: raw_name with context [network, blockchain], distance 6
                
                display_name = f"{raw_name} network"
                alt_name = f"{raw_id} network"
                
                # Create weak keyword rule
                weak_kw_rule = {
                    "keyword": raw_name.lower(),
                    "requires_context": True,
                    "required_context": ["network", "blockchain"],
                    "distance": 30, # ~6 words * 5 chars per word
                    "direction": "both"
                }
                
                topic, created = Topic.objects.get_or_create(
                    name=display_name,
                    defaults={
                        "alternative_name": alt_name,
                        "topic_type": network_type,
                        "is_placeholder": False,
                        "weak_keywords": [weak_kw_rule]
                    }
                )
                
                if not created:
                    # Update existing topic's weak keywords if not already present
                    current_weak = topic.weak_keywords or []
                    if not any(w.get('keyword') == raw_name.lower() for w in current_weak):
                        current_weak.append(weak_kw_rule)
                        topic.weak_keywords = current_weak
                    
                    topic.alternative_name = alt_name
                    topic.topic_type = network_type
                    topic.save()
                
                # Set parents
                topic.parents.add(blockchain_parent)
                topic.parents.add(network_type)
                
                if created:
                    total_imported += 1
                    print(f"  [+] Created: {display_name}")
                else:
                    print(f"  [~] Updated: {display_name}")

            # Check if there is a next page
            if len(networks) < 10:
                break
                
            page += 1
            time.sleep(1) # Rate limiting safety
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    print(f"Import finished. Total new networks created: {total_imported}")

if __name__ == "__main__":
    import_blockchain_networks()
