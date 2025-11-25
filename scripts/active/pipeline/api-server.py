#!/usr/bin/env python3
"""
FastAPI server for Gemma 3 4B Commander deck builder
Provides REST API endpoint compatible with Next.js app
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel
import json
import re
import uvicorn
import os
import sqlite3
from pathlib import Path

# Get absolute paths relative to project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
os.chdir(PROJECT_ROOT)  # Change to project root
DB_PATH = PROJECT_ROOT / 'prisma' / 'dev.db'

def filter_cards_by_identity(cards: List[str], allowed_colors: List[str]) -> List[str]:
    """Filter a list of cards to only include those within the allowed color identity"""
    if not cards:
        return []
    
    # Connect to DB
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Prepare query
        placeholders = ','.join(['?'] * len(cards))
        query = f"SELECT name, colorIdentity FROM Card WHERE name IN ({placeholders})"
        
        cursor.execute(query, cards)
        results = cursor.fetchall()
        conn.close()
        
        allowed_set = set(allowed_colors)
        valid_cards = []
        
        for row in results:
            card_name = row['name']
            # Parse color identity from DB string (e.g. "W,U" or "R")
            identity_str = row['colorIdentity']
            if not identity_str:
                card_colors = set()
            else:
                card_colors = set(identity_str.split(','))
            
            # Check if card colors are subset of allowed colors
            if card_colors.issubset(allowed_set):
                valid_cards.append(card_name)
            else:
                print(f"🚫 Filtered off-color card: {card_name} (Identity: {card_colors}, Allowed: {allowed_set})")
                
        # Preserve order from original list
        filtered_ordered = [c for c in cards if c in valid_cards]
        return filtered_ordered
        
    except Exception as e:
        print(f"Error filtering cards by identity: {e}")
        return cards  # Return original list on error to be safe

# Model configuration
# Model configuration
BASE_MODEL = "models/qwen2.5-3b"
LORA_PATH = "models/commander-qwen-3b-v3/final"

# Global model and tokenizer (loaded once on startup)
model = None
tokenizer = None

app = FastAPI(
    title="Gemma Commander Deck Builder API",
    description="AI-powered Commander/EDH deck building using Gemma 3 4B",
    version="1.0.0"
)

# Enable CORS for Next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3050"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class DeckBuildRequest(BaseModel):
    commander: Optional[str] = None
    theme: str
    colors: List[str]
    powerLevel: str  # "1"-"5" (Moxfield brackets)
    useCollectionOnly: bool = False
    userCollection: Optional[str] = None

class DeckStructure(BaseModel):
    commander: str
    strategy: str
    power_level: int
    bracket: int
    card_selection: Dict
    priority_cards: List[str]

class JSONStoppingCriteria(StoppingCriteria):
    """Stops generation when a complete JSON object is formed"""
    def __init__(self, tokenizer, prompt_length):
        self.tokenizer = tokenizer
        self.prompt_length = prompt_length
        
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        # Decode only the generated part (skip prompt)
        generated_ids = input_ids[0][self.prompt_length:]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        # Find start of JSON
        json_start = text.find('{')
        if json_start == -1:
            return False
            
        # Count braces
        brace_count = 0
        in_json = False
        
        for i, char in enumerate(text):
            if i < json_start:
                continue
                
            if char == '{':
                brace_count += 1
                in_json = True
            elif char == '}':
                brace_count -= 1
                
            # If we were in JSON and now brace_count is 0, we're done
            if in_json and brace_count == 0:
                return True
                
        return False

@app.on_event("startup")
async def load_model():
    """Load model once on startup"""
    global model, tokenizer
    
    print("Loading Qwen 2.5 3B model with LoRA adapters...")
    print(f"Base model: {BASE_MODEL}")
    print(f"LoRA path: {LORA_PATH}")
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    # Load and merge LoRA weights
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True
    )
    
    model = PeftModel.from_pretrained(base_model, LORA_PATH)
    print("Merging LoRA weights...")
    model = model.merge_and_unload()
    
    # Move to XPU and optimize
    print("Moving to XPU...")
    model = model.to("xpu")
    model = ipex.optimize(model, dtype=torch.bfloat16)
    model.eval()
    
    print(f"✅ Model ready on: {next(model.parameters()).device}\n")

def clean_and_parse_output(raw_output: str) -> Optional[Dict]:
    """Extract and parse JSON from model output, ignoring conversational text"""
    import traceback
    
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
                # If we ran out of string while counting, it's truncated.
                # Add what we have so far as a candidate to be repaired
                candidates.append(raw_output[json_start:])
                break
        
        # If no braces found, try the whole string
        if not candidates and '{' in raw_output:
            candidates.append(raw_output[raw_output.find('{'):])
        
        # Try parsing candidates, largest first
        candidates.sort(key=len, reverse=True)
        
        valid_parses = []
        
        for json_str in candidates:
            # Try parsing as is
            try:
                obj = json.loads(json_str)
                valid_parses.append(obj)
                continue
            except json.JSONDecodeError:
                pass

            # Try repairs
            try:
                # Fix missing commas
                repaired = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
                obj = json.loads(repaired)
                valid_parses.append(obj)
                continue
            except:
                pass
            
            # Try closing truncated JSON
            clean_str = json_str.strip()
            if clean_str.endswith(','):
                clean_str = clean_str[:-1]
            
            # Try closing brackets/braces
            closers = ['}', ']}', '"]}', '"]', '"}', '}}', '}}}', '"]}}', '"}}']
            for closer in closers:
                try:
                    obj = json.loads(clean_str + closer)
                    valid_parses.append(obj)
                    # If we found a valid parse with this candidate, stop trying other closers for it
                    # But we might want to try other candidates? 
                    # Actually, if we found a parse with 'commander', we are probably good.
                    if isinstance(obj, dict) and "commander" in obj:
                        break 
                except:
                    continue
        
        # Select best parse
        for obj in valid_parses:
            if not isinstance(obj, dict):
                continue
                
            if "commander" in obj:
                return obj # Found the holy grail
            
        print(f"\n⚠️ No JSON candidate contained 'commander', attempting regex reconstruction")

        print(f"\n📦 Extracted {len(candidates)} JSON candidates but all failed to parse")
        
        # Fallback: Regex reconstruction (Improved for truncation)
        try:
            # Extract the base fields
            commander_match = re.search(r'"commander":\s*"([^"]+)"', raw_output)
            strategy_match = re.search(r'"strategy":\s*"([^"]+)"', raw_output)
            
            # Power level and bracket are optional/defaultable
            power_match = re.search(r'"power_level":\s*(\d+)', raw_output)
            bracket_match = re.search(r'"bracket":\s*(\d+)', raw_output)
            
            if not (commander_match and strategy_match):
                print("Missing critical fields (commander/strategy) in truncated output")
                return None
            
            result = {
                "commander": commander_match.group(1),
                "strategy": strategy_match.group(1),
                "power_level": int(power_match.group(1)) if power_match else 3,
                "bracket": int(bracket_match.group(1)) if bracket_match else 3
            }
            
            # Extract card_selection - try to parse up to the closing }
            sel_start = raw_output.find('"card_selection":')
            if sel_start > 0:
                # Find the opening { after "card_selection":
                brace_start = raw_output.find('{', sel_start)
                if brace_start > 0:
                    # Try to find the matching closing brace, or just take what we have
                    brace_count = 0
                    brace_end = -1
                    for i in range(brace_start, len(raw_output)):
                        if raw_output[i] == '{':
                            brace_count += 1
                        elif raw_output[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                brace_end = i + 1
                                break
                    
                    selection_str = ""
                    if brace_end > 0:
                        selection_str = raw_output[brace_start:brace_end]
                    else:
                        # Truncated inside card_selection
                        selection_str = raw_output[brace_start:] + "}}" # Try to close it
                    
                    try:
                        parsed_selection = json.loads(selection_str)
                        if isinstance(parsed_selection, list):
                            print("⚠️ Warning: card_selection is a list, wrapping in default structure")
                            # Attempt to guess it's a list of priority cards or filters
                            result["card_selection"] = {
                                "creatures": {"count": 20, "filters": ["type:creature"]},
                                "lands": {"count": 36, "filters": ["type:land"]},
                                "other": parsed_selection
                            }
                        else:
                            result["card_selection"] = parsed_selection
                    except:
                        # If card_selection is broken, try to regex extract categories
                        print("Failed to parse card_selection JSON, attempting regex extraction")
                        
                        # Manual reconstruction
                        manual_selection = {}
                        categories = ["creatures", "lands", "ramp", "removal", "board_wipes", "tutors", "protection", "instants", "sorceries", "artifacts", "enchantments", "planeswalkers"]
                        
                        for cat in categories:
                            # Look for "category": {"count": N
                            cat_match = re.search(f'"{cat}":\s*\{{"count":\s*(\d+)', raw_output)
                            if cat_match:
                                manual_selection[cat] = {
                                    "count": int(cat_match.group(1)),
                                    "filters": [] # We can't easily extract filters via regex, but count is most important
                                }
                        
                        if manual_selection:
                            result["card_selection"] = manual_selection
                            print(f"✅ Manually extracted {len(manual_selection)} categories via regex")
                        else:
                            print("❌ Failed to extract any categories via regex")

            # Extract priority_cards (all quoted strings after "priority_cards": [)
            priority_match = re.search(r'"priority_cards":\s*\[(.*)', raw_output, re.DOTALL)
            if priority_match:
                cards_str = priority_match.group(1)
                # Stop at closing bracket if present
                end_bracket = cards_str.find(']')
                if end_bracket > 0:
                    cards_str = cards_str[:end_bracket]
                
                # Extract all complete strings
                priority_cards = re.findall(r'"([^"]+)"', cards_str)
                result["priority_cards"] = priority_cards
            else:
                result["priority_cards"] = []
                
            print(f"✅ Reconstructed JSON from truncated output ({len(result.get('priority_cards', []))} priority cards)")
            return result
            
        except Exception as e:
            print(f"Error during regex reconstruction: {e}")
            return None
            
    except Exception as e:
        print(f"Error parsing output: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_deck_structure(request: DeckBuildRequest) -> DeckStructure:
    """Generate deck structure using the model"""
    global model, tokenizer
    
    if model is None or tokenizer is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # Map Moxfield bracket to power level
    bracket_to_power = {
        "1": 4,  # Bracket 1 = precon level = power 4
        "2": 5,  # Bracket 2 = casual = power 5-6
        "3": 7,  # Bracket 3 = optimized = power 7
        "4": 8,  # Bracket 4 = high power = power 8
        "5": 9,  # Bracket 5 = cEDH = power 9-10
    }
    
    power_level = bracket_to_power.get(request.powerLevel, 7)
    
    # Build prompt - use exact training format
    if request.commander:
        prompt = f"Build a Commander deck with {request.commander} focused on {request.theme.lower()} at power level {power_level}"
    else:
        colors_text = "/".join(request.colors)
        prompt = f"Build a Commander deck in {colors_text} colors focused on {request.theme.lower()} at power level {power_level}"
    
    # Add explicit instructions for JSON only and card count
    prompt += ' Allocate exactly 99 cards total (excluding commander). Respond ONLY with valid JSON in this format: {"commander": "...", "strategy": "...", "card_selection": {"creatures": {"count": N, "filters": [...]}, ...}, "priority_cards": [...]}.'
    
    # Add tribal/kindred-specific instructions
    theme_lower = request.theme.lower()
    if 'tribal' in theme_lower or 'kindred' in theme_lower:
        # Extract creature type from theme (e.g., "Kindred - Cats" -> "Cat")
        import re
        type_match = re.search(r'(?:tribal|kindred)[-_\s]+(\w+)', theme_lower)
        if type_match:
            raw_type = type_match.group(1).lower()
            irregular_plurals = {
                'elves': 'Elf',
                'wolves': 'Wolf',
                'dwarves': 'Dwarf',
                'merfolk': 'Merfolk'
            }
            if raw_type in irregular_plurals:
                creature_type = irregular_plurals[raw_type]
            else:
                creature_type = raw_type.rstrip('s').capitalize()
            # Be very explicit about the filter format
            prompt += f' For creatures, use filter: {{"subtypes": ["{creature_type}"]}} to select {creature_type} creatures. For other spells (instants, sorceries, enchantments, artifacts), try to include cards that mention {creature_type} in their text.'
    
    # Add budget constraint for lower brackets
    if int(request.powerLevel) <= 2:
        prompt += " Do not use cards over $20."
    
    print(f"\nGenerating deck: {prompt}")
    
    # Base model: simple completion format (no chat template)
    # Model completes: "INSTRUCTION\n\n{JSON output}"
    formatted_prompt = f"{prompt}\n\n"
    
    # Generate
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to("xpu")
    prompt_length = inputs['input_ids'].shape[1]
    
    stopping_criteria = StoppingCriteriaList([JSONStoppingCriteria(tokenizer, prompt_length)])
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1500,
            temperature=0.5,  # Optimized: lower temp = faster, more focused output
            top_p=0.85,  # Optimized: slightly reduced for faster sampling
            repetition_penalty=1.2,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stopping_criteria=stopping_criteria,
            use_cache=True  # Optimized: enable KV cache for faster generation
        )
    
    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_only = generated[len(prompt):].strip()
    
    print(f"\n{'='*70}")
    print(f"GENERATION DEBUG")
    print(f"{'='*70}")
    print(f"Generated {len(outputs[0]) - len(inputs['input_ids'][0])} tokens")
    print(f"Prompt length: {len(inputs['input_ids'][0])} tokens")
    print(f"\nFull raw output (first 1000 chars):\n{generated_only[:1000]}")
    print(f"\n...\n")
    print(f"Last 500 chars of output:\n{generated_only[-500:]}")
    print(f"{'='*70}\n")
    
    # Parse output
    parsed = clean_and_parse_output(generated_only)
    
    if not parsed:
        print("ERROR: Failed to parse output")
        print(f"Full output:\n{generated_only}")
        raise HTTPException(status_code=500, detail="Failed to parse model output")
    
    # Validate required fields
    # Relaxed validation: power_level and bracket are sometimes omitted by the model
    required_fields = ["commander", "strategy", "card_selection"]
    for field in required_fields:
        if field not in parsed:
            print(f"❌ Missing required field: {field}")
            raise HTTPException(status_code=500, detail=f"Missing required field: {field}")
            
    # Fill in defaults if missing
    if "power_level" not in parsed:
        parsed["power_level"] = power_level  # Use the one calculated from request
    if "bracket" not in parsed:
        parsed["bracket"] = int(request.powerLevel) if request.powerLevel.isdigit() else 3
    if "priority_cards" not in parsed:
        parsed["priority_cards"] = []
    
    # HARD LIMIT: Cap priority_cards at 30 (training had 20, but allow some buffer)
    if "priority_cards" in parsed and isinstance(parsed["priority_cards"], list):
        # Remove duplicates while preserving order
        seen = set()
        unique_priority = []
        for card in parsed["priority_cards"]:
            if card not in seen and not card.startswith('A-'):  # Skip Arena cards
                unique_priority.append(card)
                seen.add(card)
            if len(unique_priority) >= 30:
                break
        parsed["priority_cards"] = unique_priority
        print(f"✂️  Trimmed priority_cards to {len(unique_priority)} unique cards")
        
        # STRICT COLOR IDENTITY FILTERING
        # Filter out cards that don't match the requested colors (prevents off-color suggestions)
        if request.colors:
            original_count = len(unique_priority)
            parsed["priority_cards"] = filter_cards_by_identity(unique_priority, request.colors)
            filtered_count = len(parsed["priority_cards"])
            if filtered_count < original_count:
                print(f"🎨 Filtered {original_count - filtered_count} off-color cards")

    # ENFORCE MINIMUM LAND COUNT
    # Users expect ~35-36 lands. Model sometimes goes low (28-30).
    if "card_selection" in parsed and "lands" in parsed["card_selection"]:
        land_spec = parsed["card_selection"]["lands"]
        if isinstance(land_spec, dict):
            current_count = land_spec.get("count", 0)
            # Bracket 1-2 might want more, 3-4 might want fewer, but 33 is a safe floor
            MIN_LANDS = 35
            if current_count < MIN_LANDS:
                print(f"🔧 Boosting land count from {current_count} to {MIN_LANDS}")
                parsed["card_selection"]["lands"]["count"] = MIN_LANDS
    
    return DeckStructure(**parsed)

@app.post("/api/deck/generate", response_model=DeckStructure)
async def generate_deck(request: DeckBuildRequest):
    """
    Generate a Commander deck structure
    
    This returns the structured deck plan (card_selection filters + priority cards).
    Use the /api/deck/execute endpoint to convert this into a complete 100-card decklist.
    """
    try:
        structure = generate_deck_structure(request)
        return structure
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": BASE_MODEL,
        "lora": LORA_PATH,
        "device": str(next(model.parameters()).device) if model else "not loaded"
    }

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Gemma Commander Deck Builder API",
        "version": "1.0.0",
        "endpoints": {
            "generate": "POST /api/deck/generate",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    print("="*70)
    print("QWEN 2.5 3B COMMANDER DECK BUILDER API")
    print("="*70)
    print("\nStarting FastAPI server...")
    print("API will be available at: http://localhost:8000")
    print("Docs available at: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
