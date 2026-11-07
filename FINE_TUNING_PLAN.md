# Fine-Tuning a Commander Deck Building Model

## Overview
Train a specialized AI model that understands Magic: The Gathering Commander format rules, card interactions, and deck building strategy using your existing data.

## Why Fine-Tuning Makes Sense

### Your Unique Data Assets
1. **31,483 cards** with EDHREC rankings, power levels, saltiness scores, tags
2. **MTGJson metadata**: card types, color identity, mana costs, oracle text
3. **EDHREC data**: Commander popularity, synergy scores, combos
4. **Your database**: Pre-computed tags, classifications, game-changer badges
5. **Generated decks**: User feedback on what works (future data)

### Advantages Over Generic Models
- ✅ **Understands Commander rules**: Color identity, singleton format, 100-card requirement
- ✅ **Knows card pool**: Won't hallucinate fake cards
- ✅ **Better synergy**: Learns from EDHREC patterns
- ✅ **Cost-effective**: Smaller specialized model > large generic model
- ✅ **Fast inference**: 3-7B models run great on Intel Arc

## Training Approaches (Ranked by Effort)

### Option 1: Fine-Tune Existing Model (RECOMMENDED)
**Best for**: Getting production-quality results in days, not months

**Base Models** (pick one):
- **Phi-3.5 Mini (3.8B)** - Microsoft, optimized for Intel, good instruction following
- **Llama 3.2 3B** - Meta, strong reasoning, open source
- **Qwen 2.5 7B** - Alibaba, excellent structured output, larger

**Training Method**: LoRA (Low-Rank Adaptation)
- Trains only 1-5% of model parameters
- Fast: 4-12 hours on Intel Arc GPU
- Low memory: Works with 16GB VRAM
- Quality: 85-95% of full fine-tuning

**Data Format**: Instruction-tuning dataset
```json
{
  "instruction": "Build a Golgari (Black-Green) Commander deck with Meren of Clan Nel Toth as commander. Theme: Graveyard recursion. Power level: 7.",
  "output": "# Meren of Clan Nel Toth - Graveyard Recursion\n\n## Commander (1)\n1x Meren of Clan Nel Toth\n\n## Creatures (35)\n1x Sakura-Tribe Elder\n1x Eternal Witness\n...",
  "context": "EDHREC Rank: 1250, Power: 8.5, Synergy: recursion, sacrifice"
}
```

**Training Size Needed**:
- Minimum: 500 high-quality deck examples
- Good: 2,000-5,000 decks
- Excellent: 10,000+ decks

---

### Option 2: Synthetic Data Generation (FAST START)
**Best for**: Starting training immediately with existing data

**Process**:
1. Use Gemini to generate 1,000 training examples
2. Prompt: "Generate a Commander deck for [random commander] with [random theme]"
3. Validate outputs (color identity, format rules)
4. Fine-tune smaller model on this dataset
5. Iterate: Use fine-tuned model to generate more training data

**Advantages**:
- Start training today (no manual deck collection)
- Scalable (generate 10,000 examples overnight)
- Quality control via validation scripts

**Disadvantages**:
- May inherit Gemini's biases
- Needs validation to ensure correctness

---

### Option 3: Scrape Real Decklists (HIGH QUALITY)
**Best for**: Learning from actual player decks

**Sources**:
- **EDHREC**: 500,000+ Commander decklists (already have scraper)
- **Moxfield**: Public decklists with descriptions
- **MTGTop8**: Tournament-winning lists
- **Archidekt**: User-created decks with tags
- **TappedOut**: Large community database

**Data Structure**:
```typescript
{
  commander: "Meren of Clan Nel Toth",
  theme: "Graveyard Recursion",
  colors: ["B", "G"],
  powerLevel: 7,
  cards: [
    { name: "Sakura-Tribe Elder", category: "Creatures", tags: ["ramp", "sacrifice"] },
    ...
  ],
  strategy: "Abuse experience counters to recur value creatures...",
  upvotes: 245,  // Quality signal
  comments: 18   // Engagement signal
}
```

**Collection Goal**: 10,000-50,000 real decks

---

### Option 4: Hybrid Approach (RECOMMENDED PATH)
**Combine all methods for best results**

**Phase 1: Quick Start (Week 1)**
1. Generate 1,000 synthetic decks with Gemini
2. Add your 31,483 cards as context knowledge
3. Fine-tune Phi-3.5 Mini (12 hours training)
4. Test quality vs. Gemini baseline

**Phase 2: Real Data (Weeks 2-3)**
1. Scrape 5,000 EDHREC decklists
2. Scrape 2,000 Moxfield high-rated decks
3. Re-train model with real + synthetic data
4. Compare quality improvement

**Phase 3: Continuous Learning (Ongoing)**
1. Collect user-generated decks from your app
2. Track which decks get exported/saved (quality signal)
3. Monthly re-training with new data
4. A/B test model versions

---

## Training Pipeline Architecture

```
┌─────────────────────────────────────────────┐
│  DATA SOURCES                               │
├─────────────────────────────────────────────┤
│  1. MTGJson (31,483 cards)                  │
│  2. Your Database (tags, power, saltiness)  │
│  3. EDHREC Scraper (decklists + synergies)  │
│  4. Moxfield Scraper (rated decks)          │
│  5. Gemini Synthetic Generation             │
│  6. MTG Comprehensive Rules (text corpus)   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  DATA PREPARATION                           │
├─────────────────────────────────────────────┤
│  - Parse decklists to structured format     │
│  - Validate color identity rules            │
│  - Compute power levels & synergy scores    │
│  - Augment with EDHREC rank & tags          │
│  - Split train/validation/test (80/10/10)   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  TRAINING (OpenVINO + Intel Arc)            │
├─────────────────────────────────────────────┤
│  Framework: HuggingFace Transformers + PEFT │
│  Method: LoRA fine-tuning                   │
│  Base: Phi-3.5-mini-instruct (3.8B)         │
│  Epochs: 3-5                                │
│  Batch Size: 4 (gradient accumulation)      │
│  Time: 8-12 hours on Intel Arc B50 Pro      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  EVALUATION                                 │
├─────────────────────────────────────────────┤
│  - Color identity accuracy (99%+ required)  │
│  - Format compliance (100-card singleton)   │
│  - EDHREC rank correlation                  │
│  - Human evaluation (5 decks per version)   │
│  - A/B test vs. Gemini                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  DEPLOYMENT                                 │
├─────────────────────────────────────────────┤
│  - Export to OpenVINO IR format             │
│  - Optimize for Intel Arc GPU inference     │
│  - Deploy to Flask API service              │
│  - Monitor quality metrics                  │
└─────────────────────────────────────────────┘
```

---

## Data Collection Scripts

### Script 1: Export Your Database to Training Format
```python
# scripts/export-training-data.py
"""
Export your card database + metadata to training format
"""
from prisma import Prisma
import json
import asyncio

async def export_card_knowledge():
    prisma = Prisma()
    await prisma.connect()
    
    # Get all cards with metadata
    cards = await prisma.card.find_many(
        include={
            'tags': True
        }
    )
    
    training_data = []
    
    # Create card knowledge entries
    for card in cards:
        entry = {
            "instruction": f"What is {card.name}?",
            "output": f"{card.name} is a {card.typeLine} with mana cost {card.manaCost}. "
                     f"Oracle text: {card.oracleText}. "
                     f"Color identity: {card.colorIdentity}. "
                     f"EDHREC rank: {card.edhrecRank}. "
                     f"Power level: {card.powerLevel}. "
                     f"Saltiness: {card.saltiness}. "
                     f"Tags: {', '.join(card.tags)}.",
            "type": "card_knowledge"
        }
        training_data.append(entry)
    
    # Save to JSONL
    with open('data/training/card_knowledge.jsonl', 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')
    
    print(f"Exported {len(training_data)} card knowledge entries")
    await prisma.disconnect()

asyncio.run(export_card_knowledge())
```

### Script 2: Generate Synthetic Training Data
```python
# scripts/generate-synthetic-decks.py
"""
Use Gemini to generate training examples
"""
import google.generativeai as genai
import random
import json
from prisma import Prisma
import asyncio
import time

THEMES = [
    "Aggro", "Control", "Midrange", "Combo", "Voltron", "Aristocrats",
    "Tokens", "Tribal", "Landfall", "Storm", "Group Hug", "Stax",
    "Reanimator", "Spellslinger", "Lifegain", "Mill", "Sacrifice",
    "Artifact", "Enchantment", "Graveyard", "Blink", "Ramp"
]

async def generate_training_decks(num_decks=1000):
    prisma = Prisma()
    await prisma.connect()
    
    # Get random commanders
    commanders = await prisma.card.find_many(
        where={'isCommander': True},
        take=200,
        order_by={'edhrecRank': 'asc'}
    )
    
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    training_data = []
    
    for i in range(num_decks):
        commander = random.choice(commanders)
        theme = random.choice(THEMES)
        power_level = random.randint(4, 9)
        
        prompt = f"""Generate a Commander deck with the following parameters:
        Commander: {commander.name}
        Theme: {theme}
        Power Level: {power_level}/10
        Colors: {commander.colorIdentity}
        
        Output a complete 100-card decklist in this format:
        ## Commander (1)
        1x Card Name
        
        ## Creatures (30-40)
        1x Card Name
        ...
        """
        
        try:
            response = model.generate_content(prompt)
            
            entry = {
                "instruction": f"Build a {'/'.join(commander.colorIdentity)} Commander deck with {commander.name}. Theme: {theme}. Power level: {power_level}.",
                "output": response.text,
                "metadata": {
                    "commander": commander.name,
                    "theme": theme,
                    "powerLevel": power_level,
                    "colors": commander.colorIdentity
                }
            }
            
            training_data.append(entry)
            
            if (i + 1) % 10 == 0:
                print(f"Generated {i + 1}/{num_decks} decks")
            
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"Error generating deck {i}: {e}")
            continue
    
    # Save to JSONL
    with open('data/training/synthetic_decks.jsonl', 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')
    
    print(f"Generated {len(training_data)} synthetic decks")
    await prisma.disconnect()

asyncio.run(generate_training_decks(1000))
```

### Script 3: Scrape Real Decklists
```python
# scripts/scrape-edhrec-decks.py
"""
Scrape EDHREC for real Commander decklists
"""
import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_edhrec_decklist(url):
    """Scrape a single EDHREC decklist"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Parse commander
    commander = soup.find('h1', class_='commander').text.strip()
    
    # Parse theme
    theme = soup.find('span', class_='theme').text.strip()
    
    # Parse decklist
    cards = []
    for card_elem in soup.find_all('div', class_='card-entry'):
        name = card_elem.find('span', class_='card-name').text.strip()
        category = card_elem.find('span', class_='category').text.strip()
        cards.append({'name': name, 'category': category})
    
    return {
        'commander': commander,
        'theme': theme,
        'cards': cards,
        'source': 'edhrec',
        'url': url
    }

def scrape_top_commanders(limit=100):
    """Scrape top commanders and their average decklists"""
    url = 'https://edhrec.com/commanders'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    commander_links = []
    for link in soup.find_all('a', class_='commander-link'):
        commander_links.append('https://edhrec.com' + link['href'])
        if len(commander_links) >= limit:
            break
    
    decks = []
    for i, link in enumerate(commander_links):
        try:
            deck = scrape_edhrec_decklist(link)
            decks.append(deck)
            print(f"Scraped {i+1}/{limit}: {deck['commander']}")
            time.sleep(1)  # Be nice to EDHREC servers
        except Exception as e:
            print(f"Error scraping {link}: {e}")
            continue
    
    return decks

# Run scraper
decks = scrape_top_commanders(1000)

# Save to file
with open('data/training/edhrec_decks.jsonl', 'w') as f:
    for deck in decks:
        f.write(json.dumps(deck) + '\n')

print(f"Scraped {len(decks)} EDHREC decklists")
```

---

## Fine-Tuning Script (LoRA)

```python
# scripts/train-commander-model.py
"""
Fine-tune Phi-3.5 Mini for Commander deck building
"""
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import os

# Configuration
MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"
OUTPUT_DIR = "./models/commander-phi-3.5-lora"
TRAINING_DATA = "data/training/combined_training.jsonl"

# Load model and tokenizer
print("Loading base model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

# LoRA configuration
print("Applying LoRA configuration...")
lora_config = LoraConfig(
    r=16,  # Rank
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

print(f"Trainable parameters: {model.print_trainable_parameters()}")

# Load dataset
print("Loading training data...")
dataset = load_dataset('json', data_files=TRAINING_DATA, split='train')

# Format data for training
def format_instruction(example):
    instruction = example['instruction']
    output = example['output']
    text = f"<|user|>\n{instruction}<|end|>\n<|assistant|>\n{output}<|end|>"
    return tokenizer(text, truncation=True, max_length=2048)

tokenized_dataset = dataset.map(format_instruction, remove_columns=dataset.column_names)

# Training arguments
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    fp16=True,
    save_strategy="epoch",
    logging_steps=10,
    optim="adamw_torch",
    warmup_steps=100,
    report_to="none"
)

# Data collator
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator
)

# Train
print("Starting training...")
trainer.train()

# Save model
print("Saving model...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"Training complete! Model saved to {OUTPUT_DIR}")
```

---

## Expected Training Time & Costs

### Hardware: Intel Arc B50 Pro (16GB VRAM)
- **Phi-3.5 Mini (3.8B)**: 8-12 hours (1,000 examples)
- **Llama 3.2 3B**: 8-12 hours
- **Qwen 2.5 7B**: 16-24 hours (may need gradient checkpointing)

### Data Collection
- **Synthetic (Gemini)**: 1,000 decks = $2-5 (API costs)
- **Scraping**: Free, but time-intensive (rate limiting)

### Storage Requirements
- **Training data**: 500MB - 2GB (10,000 decks)
- **Base model**: 7-14GB
- **Fine-tuned model**: +100-500MB (LoRA weights)
- **Total**: ~20GB

---

## Quality Metrics

### Automatic Evaluation
1. **Color Identity Accuracy**: 99%+ required
   - Parse every card in generated deck
   - Verify color identity ⊆ commander identity

2. **Format Compliance**: 100% required
   - Exactly 100 cards (including commander)
   - Singleton format (no duplicates except basic lands)
   - No banned cards

3. **Card Validity**: 100% required
   - All cards exist in your database
   - No hallucinated cards

4. **Power Level Consistency**
   - Compare avg card power level to target
   - Should be within ±1.0 of target

### Human Evaluation (Sample 20 decks)
1. **Synergy**: Do cards work together? (1-10)
2. **Strategy clarity**: Clear game plan? (1-10)
3. **Playability**: Would you play this? (1-10)
4. **Comparison**: Better/worse/same as Gemini? (Rank)

---

## Implementation Roadmap

### Week 1: Data Collection
- [ ] Export card database to training format (1 hour)
- [ ] Generate 1,000 synthetic decks with Gemini (2 hours)
- [ ] Set up EDHREC scraper (2 hours)
- [ ] Scrape 2,000 EDHREC decklists (4 hours)
- [ ] Combine and validate training data (2 hours)

### Week 2: Training Setup
- [ ] Install training dependencies in OpenVINO env (1 hour)
- [ ] Download base model (Phi-3.5 Mini) (30 min)
- [ ] Test training script on 10 examples (2 hours)
- [ ] Run full training (12 hours)
- [ ] Evaluate model quality (4 hours)

### Week 3: Integration
- [ ] Export to OpenVINO IR format (1 hour)
- [ ] Create Flask API service (4 hours)
- [ ] Integrate with Next.js app (4 hours)
- [ ] A/B test vs. Gemini (ongoing)
- [ ] Collect user feedback (ongoing)

### Ongoing: Continuous Improvement
- [ ] Scrape 1,000 new decks monthly
- [ ] Collect user-generated decks
- [ ] Re-train quarterly with new data
- [ ] Track quality metrics dashboard

---

## Advantages of This Approach

### vs. Using Gemini Forever
- ✅ **No rate limits** (unlimited deck generation)
- ✅ **No API costs** ($0 per deck vs. $0.01-0.05)
- ✅ **Faster** (local inference, no network latency)
- ✅ **Privacy** (deck data stays local)
- ✅ **Customizable** (tune for your specific use cases)

### vs. Generic Local Models
- ✅ **Commander expertise** (knows color identity rules)
- ✅ **Card knowledge** (trained on your database)
- ✅ **No hallucinations** (only uses real cards)
- ✅ **Better synergies** (learned from EDHREC)
- ✅ **Smaller, faster** (3.8B specialized > 70B generic)

### Long-term Value
- Your data becomes an asset (moat)
- Model improves as you collect more decks
- Community contributions (users share decks)
- Potential to offer as API to other tools

---

## Next Steps

### Option A: Synthetic Quick Start (Fastest)
1. Run `generate-synthetic-decks.py` (today)
2. Fine-tune Phi-3.5 Mini overnight
3. Test quality tomorrow
4. Decision: Good enough or need real data?

### Option B: Real Data First (Highest Quality)
1. Enhance EDHREC scraper (1-2 days)
2. Scrape 5,000 real decklists (2-3 days)
3. Fine-tune with real data
4. Higher quality but slower start

### Option C: Hybrid (Recommended)
1. Generate 500 synthetic decks today
2. Start scraping EDHREC tonight (background)
3. Fine-tune on synthetic data (v1)
4. Re-train with real data next week (v2)
5. Compare quality improvement

**My recommendation**: Start with Option C to get fast feedback while collecting high-quality data.

Would you like me to start building the data collection scripts?
