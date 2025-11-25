import sys
import os

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from synergy_engine import SynergyEngine

def test_combo_detection():
    print("🧪 Testing Combo Detection...")
    
    # Initialize engine with DB path
    engine = SynergyEngine(db_path='prisma/dev.db')
    
    # Test Case 1: Kiki-Jiki (should suggest Zealous Conscripts or similar if in DB)
    # We need to ensure the DB has this combo. 
    # If the scraper hasn't run yet, this might fail unless we mock it or use hardcoded ones.
    # But wait, the engine checks BOTH hardcoded and DB.
    # Let's test a DB-only combo if possible, or just verify the logic works.
    
    deck = ["Kiki-Jiki, Mirror Breaker", "Mountain", "Sol Ring"]
    print(f"\nDeck: {deck}")
    
    suggestions = engine.find_synergies(deck, ['R'])
    print(f"Suggestions: {suggestions}")
    
    if "Zealous Conscripts" in suggestions:
        print("✅ SUCCESS: Found Zealous Conscripts via Hardcoded/DB")
    else:
        print("⚠️ NOTE: Zealous Conscripts not found (might be missing from DB if not hardcoded)")

    # Test Case 2: Thassa's Oracle (Hardcoded check)
    deck2 = ["Thassa's Oracle", "Island"]
    print(f"\nDeck: {deck2}")
    suggestions2 = engine.find_synergies(deck2, ['U', 'B'])
    print(f"Suggestions: {suggestions2}")
    
    if "Demonic Consultation" in suggestions2:
        print("✅ SUCCESS: Found Demonic Consultation")

if __name__ == "__main__":
    test_combo_detection()
