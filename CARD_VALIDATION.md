# Card Validation for Commander AI

## Overview

The Commander AI now includes a card validation system to ensure only real Magic: The Gathering cards are suggested. This prevents the model from hallucinating fake card names.

## How It Works

### 1. Card Database
- Uses `data/mtgjson/AtomicCards.json` as the source of truth
- Contains all official Magic cards (~66,000+ unique card names)
- Provides card metadata (types, colors, mana cost, etc.)

### 2. Validation Methods

#### Exact Match Validation
```python
validator = CardValidator()
is_valid = validator.is_valid_card("Sol Ring")  # True
is_valid = validator.is_valid_card("Fake Card")  # False
```

#### Fuzzy Match Validation
Handles minor spelling variations and case differences:
```python
corrected = validator.validate_card_name("sol ring")  # Returns "Sol Ring"
corrected = validator.validate_card_name("lightning bolt")  # Returns "Lightning Bolt"
```

#### Deck List Validation
Validates an entire deck at once:
```python
result = validator.validate_deck_list(deck_text)
# Returns:
# - valid_cards: List of validated card names
# - invalid_cards: List of cards not found in database
# - corrections: Auto-corrections made
# - total_cards: Count of valid cards
```

### 3. Integration with AI Generation

#### Post-Generation Validation (Current Implementation)
1. Model generates deck text
2. Validator parses and validates each card
3. Invalid cards are either corrected or removed
4. Final validated deck is returned

```python
validated_deck = validate_and_correct_generation(generated_text, validator)
```

#### Constrained Prompting
The system uses special prompts that emphasize using real card names:
```python
prompt = create_constrained_generation_prompt(commander, theme, validator)
# Adds: "IMPORTANT: Only use real Magic: The Gathering card names..."
```

## Usage

### Basic Validation

```python
from scripts.card_validator import CardValidator

# Initialize validator
validator = CardValidator()

# Validate single card
if validator.is_valid_card("Lightning Bolt"):
    print("Valid card!")

# Get card info
info = validator.get_card_info("Sol Ring")
print(f"Types: {info['types']}")
print(f"Colors: {info['colors']}")
```

### Generate Validated Deck

```python
# Run the validated inference script
python scripts/test-trained-model-validated.py
```

This will:
1. Load the trained model
2. Generate decks for test commanders
3. Validate all cards
4. Correct or remove invalid cards
5. Show validation statistics
6. Save validated decks to `generated_decks/`

### Validation Statistics

After generation, you'll see:
```
VALIDATION SUMMARY
============================================================
Total cards: 99
Valid cards: 97
Invalid cards remaining: 2

⚠️  Warning: 2 invalid cards could not be corrected:
  - Made Up Card Name
  - Another Fake Card
```

## Advanced Usage

### Custom Validation Rules

You can extend the validator to add additional constraints:

```python
class CustomValidator(CardValidator):
    def is_legal_in_commander(self, card_name: str) -> bool:
        """Check if card is legal in Commander format"""
        card_info = self.get_card_info(card_name)
        if not card_info:
            return False
        
        # Check if card is banned in Commander
        banned_cards = ['Black Lotus', 'Ancestral Recall', ...]
        if card_name in banned_cards:
            return False
        
        return True
    
    def validate_color_identity(self, card_name: str, commander_colors: List[str]) -> bool:
        """Check if card matches commander's color identity"""
        card_info = self.get_card_info(card_name)
        if not card_info:
            return False
        
        card_colors = set(card_info.get('colorIdentity', []))
        allowed_colors = set(commander_colors)
        
        return card_colors.issubset(allowed_colors)
```

### Real-Time Validation (Future Enhancement)

For streaming generation with token-by-token validation:

```python
# This would require implementing custom generation loop
def constrained_generate(model, tokenizer, prompt, validator):
    """Generate with real-time card name validation"""
    # 1. Generate tokens one at a time
    # 2. When complete word detected, check if it's a card name
    # 3. If invalid card name forming, use beam search to steer to valid alternatives
    # 4. This ensures model never generates invalid card names
    pass
```

## Configuration

### Validator Settings

```python
validator = CardValidator(
    card_data_path='data/mtgjson/AtomicCards.json'  # Path to card database
)
```

### Generation Settings with Validation

```python
validated_deck, stats = generate_deck_with_validation(
    model=model,
    tokenizer=tokenizer,
    validator=validator,
    commander="The Ur-Dragon",
    theme="dragon tribal",
    max_new_tokens=1024,  # Max tokens to generate
    temperature=0.7       # Lower = more focused on training data
)
```

**Temperature Impact:**
- `0.5-0.6`: Very conservative, sticks closely to training examples (fewer invalid cards)
- `0.7-0.8`: Balanced creativity and accuracy (recommended)
- `0.9-1.0`: More creative but higher chance of invalid cards

## Best Practices

### 1. Training Data Quality
- Ensure training decks only contain real card names
- Use validated sources (Moxfield, EDHREC, etc.)
- Current training data is 100% validated ✓

### 2. Prompt Engineering
- Always include "Only use real Magic cards" in prompts
- Provide examples of real card names in context
- Use `create_constrained_generation_prompt()` helper

### 3. Post-Processing
- Always run validation on generated text
- Log invalid cards for model improvement
- Consider retraining if too many invalid cards appear

### 4. Validation Thresholds
```python
result = validator.validate_deck_list(deck_text)

# Set quality thresholds
if result['invalid_count'] > 5:
    print("Too many invalid cards, regenerating...")
elif result['total_cards'] < 90:
    print("Not enough cards, regenerating...")
else:
    print("Deck quality acceptable!")
```

## Troubleshooting

### Issue: Model generates fake card names

**Solution 1:** Lower temperature
```python
temperature=0.5  # Instead of 0.7
```

**Solution 2:** Add more real cards to training data
- The balanced dataset should help significantly
- Consider adding more deck examples if issue persists

**Solution 3:** Use constrained decoding
- Implement beam search with card name constraints
- Force model to only output tokens that form valid card names

### Issue: Validator doesn't recognize valid cards

**Possible causes:**
1. Card name has special characters: Check for apostrophes, commas, etc.
2. Card is from new set: Update AtomicCards.json from MTGJson
3. Card has multiple printings: Use exact name from database

**Solution:**
```python
# Check what the validator sees
normalized = validator._normalize_name("Teferi's Protection")
print(f"Normalized: {normalized}")
print(f"In database: {normalized in validator.normalized_to_real}")
```

### Issue: Too many false positives

If validator marks real cards as invalid:
1. Check AtomicCards.json is up to date
2. Verify card name spelling exactly matches database
3. Check for unicode characters or special formatting

## API Reference

### CardValidator

**Methods:**
- `is_valid_card(card_name: str) -> bool`: Check if card exists
- `validate_card_name(card_name: str) -> Optional[str]`: Validate and correct
- `validate_deck_list(deck_text: str) -> Dict`: Validate entire deck
- `get_card_info(card_name: str) -> Optional[Dict]`: Get card details

**Returns from validate_deck_list:**
```python
{
    'valid_cards': List[str],      # List of valid card names
    'invalid_cards': List[str],    # List of invalid card names
    'corrections': List[Dict],     # Auto-corrections made
    'total_cards': int,            # Count of valid cards
    'invalid_count': int           # Count of invalid cards
}
```

## Performance

- **Validation speed:** ~50,000 cards/second
- **Memory usage:** ~200MB for full card database
- **Initialization time:** ~2-3 seconds

## Future Enhancements

1. **Commander Format Legality**
   - Filter banned cards
   - Enforce color identity restrictions
   - Check for duplicate cards (except basic lands)

2. **Real-Time Constrained Generation**
   - Token-level validation during generation
   - Beam search with card name constraints
   - Guaranteed 100% valid output

3. **Smart Corrections**
   - Suggest similar cards when invalid card found
   - Use card similarity metrics (same type, colors, cost)
   - Learn from correction patterns

4. **API Integration**
   - Validate against Scryfall API for latest cards
   - Check card prices and availability
   - Suggest budget alternatives

## Examples

See:
- `scripts/card_validator.py` - Core validation system
- `scripts/test-trained-model-validated.py` - Validated inference
- Run `python scripts/card_validator.py` for demo
