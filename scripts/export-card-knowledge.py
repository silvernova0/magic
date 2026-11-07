"""
Export card database to training format for fine-tuning
Creates JSONL file with card knowledge entries
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Check if Prisma is available
try:
    from prisma import Prisma
except ImportError:
    print("✗ Prisma not available in OpenVINO environment")
    print("\nThis script needs to run in the main Node.js environment.")
    print("Run instead:")
    print("  node scripts/export-card-knowledge.js")
    sys.exit(1)

async def export_card_knowledge():
    """Export all cards with metadata to training format"""
    
    prisma = Prisma()
    await prisma.connect()
    
    print("Fetching cards from database...")
    
    # Get all cards with their metadata
    cards = await prisma.card.find_many(
        where={
            'oracleText': {'not': None}  # Skip tokens/lands without rules
        },
        order_by={'edhrecRank': 'asc'}
    )
    
    print(f"Found {len(cards)} cards")
    
    training_data = []
    
    # Create multiple training formats for each card
    for i, card in enumerate(cards):
        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1}/{len(cards)} cards...")
        
        # Format 1: Card description
        if card.oracleText:
            training_data.append({
                "instruction": f"Describe the Magic: The Gathering card '{card.name}'.",
                "output": f"{card.name} is a {card.typeLine} with mana cost {card.manaCost or 'N/A'}. "
                         f"{card.oracleText} "
                         f"Its color identity is {', '.join(card.colorIdentity) if card.colorIdentity else 'colorless'}.",
                "type": "card_description",
                "metadata": {
                    "cardName": card.name,
                    "powerLevel": card.powerLevel,
                    "edhrecRank": card.edhrecRank
                }
            })
        
        # Format 2: Commander eligibility
        if card.isCommander:
            training_data.append({
                "instruction": f"Can {card.name} be a Commander?",
                "output": f"Yes, {card.name} can be a Commander. It is a {card.typeLine} with color identity "
                         f"{', '.join(card.colorIdentity) if card.colorIdentity else 'colorless'}.",
                "type": "commander_check",
                "metadata": {
                    "cardName": card.name,
                    "isCommander": True,
                    "colorIdentity": card.colorIdentity
                }
            })
        
        # Format 3: Power level assessment
        if card.powerLevel:
            power_desc = "casual" if card.powerLevel < 4 else "focused" if card.powerLevel < 6 else "optimized" if card.powerLevel < 8 else "cEDH"
            training_data.append({
                "instruction": f"What power level is {card.name} in Commander?",
                "output": f"{card.name} has a power level of {card.powerLevel}/10, making it a {power_desc} card. "
                         f"EDHREC rank: {card.edhrecRank or 'Not ranked'}.",
                "type": "power_assessment",
                "metadata": {
                    "cardName": card.name,
                    "powerLevel": card.powerLevel,
                    "edhrecRank": card.edhrecRank
                }
            })
        
        # Format 4: Color identity
        training_data.append({
            "instruction": f"What is the color identity of {card.name}?",
            "output": f"The color identity of {card.name} is {', '.join(card.colorIdentity) if card.colorIdentity else 'colorless'}. "
                     f"This means it can only be used in Commander decks with commanders that include these colors.",
            "type": "color_identity",
            "metadata": {
                "cardName": card.name,
                "colorIdentity": card.colorIdentity
            }
        })
    
    # Save to JSONL file
    output_dir = Path(__file__).parent.parent / "data" / "training"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "card_knowledge.jsonl"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')
    
    print(f"\n✓ Exported {len(training_data)} training entries")
    print(f"✓ Saved to: {output_file}")
    print(f"✓ File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(export_card_knowledge())
