
import json
import re
from typing import Optional, Dict

def clean_and_parse_output(raw_output: str) -> Optional[Dict]:
    """Extract and parse JSON from model output, ignoring conversational text"""
    try:
        # Strip "model" prefix if present
        if raw_output.strip().startswith('model'):
            raw_output = raw_output.strip()[5:].strip()
        
        # Find JSON boundaries - extract ONLY the first complete JSON object
        # Try multiple times in case there are nested or multiple blocks
        candidates = []
        
        # Method 1: Standard brace counting
        json_start = raw_output.find('{')
        while json_start >= 0:
            brace_count = 0
            json_end = -1
            for i in range(json_start, len(raw_output)):
                if raw_output[i] == '{':
                    brace_count += 1
                elif raw_output[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end > json_start:
                candidates.append(raw_output[json_start:json_end])
                # Look for next candidate
                json_start = raw_output.find('{', json_start + 1)
            else:
                break
        
        # Try parsing candidates, largest first (usually the main deck structure)
        candidates.sort(key=len, reverse=True)
        
        for json_str in candidates:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try simple repairs
                try:
                    # Fix missing commas between fields (common LLM error)
                    # Look for " (quote) followed by newline/space then " (quote)
                    repaired = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
                    return json.loads(repaired)
                except:
                    pass
        
        print(f"\n📦 Extracted {len(candidates)} JSON candidates but all failed to parse")
        
        # Fallback: Regex reconstruction (as before, but improved)
        try:
            # Extract the base fields
            commander_match = re.search(r'"commander":\s*"([^"]+)"', raw_output)
            strategy_match = re.search(r'"strategy":\s*"([^"]+)"', raw_output)
            power_match = re.search(r'"power_level":\s*(\d+)', raw_output)
            bracket_match = re.search(r'"bracket":\s*(\d+)', raw_output)
            
            if not all([commander_match, strategy_match, power_match, bracket_match]):
                print("Missing required fields in truncated output")
                return None
            
            # Extract card_selection - try to parse up to the closing }
            # Find "card_selection": { and then count braces until balanced
            sel_start = raw_output.find('"card_selection":')
            if sel_start < 0:
                print("Could not find card_selection")
                return None
            
            # Find the opening { after "card_selection":
            brace_start = raw_output.find('{', sel_start)
            if brace_start < 0:
                return None
            
            # Count braces to find matching closing }
            brace_count = 0
            brace_end = brace_start
            for i in range(brace_start, len(raw_output)):
                if raw_output[i] == '{':
                    brace_count += 1
                elif raw_output[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        brace_end = i + 1
                        break
            
            if brace_count != 0:
                print(f"Could not find balanced braces for card_selection (count={brace_count})")
                return None
            
            selection_json_str = raw_output[brace_start:brace_end]
            
            try:
                card_selection = json.loads(selection_json_str)
            except json.JSONDecodeError as e:
                # Try repair on selection block too
                try:
                    repaired = re.sub(r'"\s*\n\s*"', '",\n"', selection_json_str)
                    card_selection = json.loads(repaired)
                except:
                    print(f"Failed to parse card_selection: {e}")
                    return None
            
            # Extract priority_cards (all quoted strings after "priority_cards": [)
            priority_match = re.search(r'"priority_cards":\s*\[(.*)', raw_output, re.DOTALL)
            priority_cards = []
            if priority_match:
                cards_str = priority_match.group(1)
                # Stop at closing bracket if possible
                end_bracket = cards_str.find(']')
                if end_bracket > 0:
                    cards_str = cards_str[:end_bracket]
                priority_cards = re.findall(r'"([^"]+)"', cards_str)
            
            # Get unique cards, limit to 30, skip Arena cards
            unique_cards = []
            seen = set()
            for card in priority_cards:
                if card not in seen and not card.startswith('A-'):
                    unique_cards.append(card)
                    seen.add(card)
                if len(unique_cards) >= 30:
                    break
            
            # Reconstruct complete JSON
            reconstructed = {
                "commander": commander_match.group(1),
                "strategy": strategy_match.group(1),
                "power_level": int(power_match.group(1)),
                "bracket": int(bracket_match.group(1)),
                "card_selection": card_selection,
                "priority_cards": unique_cards
            }
            
            print(f"✅ Reconstructed JSON from truncated output ({len(unique_cards)} priority cards)")
            return reconstructed
            
        except Exception as e:
            print(f"Error during regex reconstruction: {e}")
            return None
            
    except Exception as e:
        print(f"Error parsing output: {e}")
        import traceback
        traceback.print_exc()
        return None

# Truncated output from logs
truncated_output = """
{
  "commander": "The Ur-Dragon",
  "strategy": "tribal",
  "power_level": 7,
  "bracket": 4,
  "card_selection": {
    "lands": {
      "count": 30,
      "filters": [
        {
          "types": [
            "Land"
          ],
          "colors_within": []
        }
      ]
    },
    "ramp": {
      "count": 9,
      "filters": [
        {
          "tags": [
            "ramp"
          ],
          "cmc_max": 3,
          "reason": "Accelerate gameplan"
        }
      ]
    },
    "removal": {
      "count": 2,
      "filters": [
        {
          "tags": [
            "removal"
          ],
          "instant_speed": true,
          "reason": "Answer threats"
        }
      ]
    },
    "board_wipes": {
      "count": 1,
      "filters": [
        {
          "tags": [
            "board_wipe"
          ],
          "reason": "Reset board state"
        }
      ]
    },
    "creatures": {
      "count": 15,
      "filters": [
        {
          "types": [
            "Creature"
          ],
          "reason": "Spell payoffs and presence",
          "subtypes": null
        }
      ]
    },
    "instants": {
      "count": 20,
      "filters": [
        {
          "types": [
            "Instant"
          ],
          "reason": "Spell triggers and interaction"
        }
      ]
    },
    "sorceries": {
      "count": 15,
      "filters": [
        {
          "types": [
            "Sorcery"
          ],
          "reason": "Spell triggers and value"
        }
      ]
    },
    "planeswalkers": null,
    "artifacts": null,
    "enchantments": null
  },
  "priority_cards": [
    "Ghyrson Starn, Kelermoph",
    "An Offer You Can't Refuse",
    "Arcane Signet",
    "Artist's Talent",
    "Basilisk Collar",
    "Big Score",
    "Blasphemous Act",
    "Blood Moon",
    "Boompile",
    "Brain Freeze",
    "Brainsurge",
    "Cyclonic Rift",
    "Dramatic Reversal",
    "Flare of Duplication",
    "Generous Patron",
    "Jolene, the Plunder Queen",
    "Lotus Petal",
    "Mind Stone",
    "Orcish Bowmasters",
    "Phyrexian Metamorph",
    "Rhystic Study",
    "Shizo, Death's Storehouse",
    "Spire Garden",
    "The Great Henge",
    "Tranquil Thicket",
    "Urborg, Tomb of Yawgmoth",
    "Volcanic Island",
    "Volatile Stormdrake",
    "Wild Growth",
    "Yawgmoth's Will",
    "Zo-Zu the Punisher",
    "City of Brass",
    "Eternal Witness",
    "Aetherflux Reservoir",
    "Mox Diamond",
    "Snow-Covered Forest",
    "Snow-Covered Mountains",
    "Mountain",
    "Forest",
    "Plains",
    "Swamp",
    "Island",
    "Tropical Island",
    "Taiga",
    "Scalding Tarn",
    "Verdant Catacombs",
    "Temple Garden",
    "Wooded Foothills",
    "Flooded Strand",
    "Steam Vents",
    "Underground Sea",
    "Watery Grave",
    "Chrome Mox",
    "Hallowed Fountain",
    "Smothering Tithe",
    "Enlightened Tutor",
    "Godless Shrine",
    "Noble Hierarch",
    "Pact of Negation",
    "Mana Vault",
    "Polluted Delta",
    "Rite of Flame",
    "Silent Clearing",
    "Sol Ring",
    "Urza's Saga",
    "Llanowar Elves",
    "Pyretic Ritual",
    "Skullclamp",
    "Training Center",
    "Valakut Awakening // Valakut Stoneforge",
    "Windswept Heath",
    "Chromatic Lantern",
    "Emergence Zone",
    "Prismatic Vista",
    "Thrummingbird",
    "Marsh Flats",
    "Ancient Greenwarden",
    "Elvish Mystic",
    "Finale of Devastation",
    "Karmic Guide",
    "Lightning Greaves",
    "Sunpetal Grove",
    "Teferi, Time Raveler",
    "Reconnaissance Flight",
    "Stomping Ground",
    "Command Tower",
    "Exotic Orchard",
    "Overgrown Tomb",
    "Simian Spirit Guide",
    "Toxic Deluge
"""

print("Testing parsing...")
result = clean_and_parse_output(truncated_output)
if result:
    print("SUCCESS!")
    
    # ENFORCE MINIMUM LAND COUNT
    parsed = result
    if parsed and "card_selection" in parsed and "lands" in parsed["card_selection"]:
        land_spec = parsed["card_selection"]["lands"]
        if isinstance(land_spec, dict):
            current_count = land_spec.get("count", 0)
            # Bracket 1-2 might want more, 3-4 might want fewer, but 33 is a safe floor
            MIN_LANDS = 35
            if current_count < MIN_LANDS:
                print(f"🔧 Boosting land count from {current_count} to {MIN_LANDS}")
                parsed["card_selection"]["lands"]["count"] = MIN_LANDS
                
    print(json.dumps(result, indent=2))
else:
    print("FAILURE")
