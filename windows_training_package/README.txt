Commander Deck Builder - Windows Training Package
==================================================

Contents:
- v3_structured_training.jsonl (41 MB, 29,152 examples)
- deck_building_rules.json (strategy definitions)
- train_commander_model.py (training script)
- TRAINING_DATA_READY.md (dataset details)
- WINDOWS_RTX_TRAINING_GUIDE.md (full training guide)

Quick Start:
1. Install dependencies:
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   pip install transformers accelerate peft datasets bitsandbytes

2. Verify GPU:
   python -c "import torch; print(torch.cuda.is_available())"

3. Start training:
   python train_commander_model.py

Training time: 12-14 hours on RTX 5070 Ti
Model: Llama 3.1 8B Instruct with LoRA (rank 32)
Output: ./llama-3.1-8b-commander-lora/final/

For details, see WINDOWS_RTX_TRAINING_GUIDE.md
