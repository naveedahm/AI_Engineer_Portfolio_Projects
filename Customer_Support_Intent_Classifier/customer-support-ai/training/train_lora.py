#!/usr/bin/env python3
"""
Complete QLoRA Fine-Tuning Script for Kaggle
Runs on Free GPU (T4 x2) within 2-3 hours
"""

import os
import json
import re
import hashlib
import logging
import torch
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import gc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/kaggle/working/training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# PART 1: DATA CLEANING & PREPARATION
# ============================================

def clean_ticket_text(text: str) -> str:
    """Clean raw ticket text for training"""
    if not text:
        return ""
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    
    # Remove ticket IDs and mention tags
    text = re.sub(r'T-\d+', '', text)
    text = re.sub(r'@\w+', '[MENTION]', text)
    
    # Remove API keys and tokens
    text = re.sub(r'sk_[a-zA-Z0-9]+', '[API_KEY]', text)
    text = re.sub(r'[a-zA-Z0-9]{32,}', '[TOKEN]', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    
    # Limit length
    if len(text) > 2000:
        text = text[:2000]
    
    return text

def create_training_example(ticket: Dict) -> Dict:
    """Convert ticket to instruction format for fine-tuning"""
    
    instruction = """You are a customer support AI for CloudSaaS, a project management platform. Classify the support ticket and generate a helpful response.

INTENT CATEGORIES:
- login_issue: Problems signing in, password reset, 2FA, account locked
- billing: Subscription, invoice, payment method, refund, double charge
- feature_request: Asking for new functionality, UI improvements
- bug_report: Something not working as expected, errors, crashes
- account_management: Profile updates, team settings, permissions
- api_help: API integration, webhooks, authentication, rate limits
- data_export: Exporting projects, reports, backups, migration
- integration: Connecting with Slack, GitHub, Jira, etc.
- performance: Slow loading, timeouts, latency issues
- security: Data breach concerns, permissions, access control
- other: Anything not above

Follow this exact JSON format in your response:
{
  "intent": "category_name",
  "confidence": 0.0-1.0,
  "draft_response": "Your helpful response here"
}"""
    
    # Clean the ticket content
    cleaned_desc = clean_ticket_text(ticket.get('description', ''))
    cleaned_subject = clean_ticket_text(ticket.get('subject', ''))
    cleaned_resolution = clean_ticket_text(ticket.get('resolution', 'We are looking into this issue.'))
    
    # Build input with subject and description
    user_input = f"SUBJECT: {cleaned_subject}\nDESCRIPTION: {cleaned_desc}"
    
    # Build the expected output
    expected_output = json.dumps({
        "intent": ticket.get('intent', 'other'),
        "confidence": 0.95,
        "draft_response": cleaned_resolution
    }, indent=2)
    
    return {
        "instruction": instruction,
        "input": user_input,
        "output": expected_output
    }

# ============================================
# PART 2: DEDUPLICATION & QUALITY FILTERING
# ============================================

def deduplicate_examples(examples: List[Dict], similarity_threshold: float = 0.85):
    """Remove near-duplicate examples using semantic similarity"""
    
    logger.info(f"Starting deduplication on {len(examples)} examples...")
    
    # Load small embedding model (this will download once)
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    except:
        logger.warning("Could not load sentence transformer, using simple text matching")
        return simple_deduplicate(examples)
    
    # Create embeddings for inputs
    texts = [ex['input'] for ex in examples]
    
    # Process in batches to avoid memory issues on Kaggle
    batch_size = 256
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=True)
        embeddings.extend(batch_embeddings)
    
    embeddings = np.array(embeddings)
    
    # Find duplicates using cosine similarity
    unique_indices = []
    unique_examples = []
    
    for i in range(len(embeddings)):
        is_duplicate = False
        for j in unique_indices:
            sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
            if sim > similarity_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_indices.append(i)
            unique_examples.append(examples[i])
        
        # Progress update
        if i % 500 == 0:
            logger.info(f"Processed {i}/{len(examples)} examples...")
    
    logger.info(f"Deduplicated: {len(examples)} → {len(unique_examples)} examples")
    return unique_examples

def simple_deduplicate(examples: List[Dict]) -> List[Dict]:
    """Fallback deduplication using text hashing"""
    seen_hashes = set()
    unique_examples = []
    
    for ex in examples:
        text_hash = hashlib.md5(ex['input'].encode()).hexdigest()
        if text_hash not in seen_hashes:
            seen_hashes.add(text_hash)
            unique_examples.append(ex)
    
    logger.info(f"Hash-based deduplication: {len(examples)} → {len(unique_examples)}")
    return unique_examples

def filter_quality(examples: List[Dict]) -> List[Dict]:
    """Filter low-quality examples"""
    filtered = []
    
    for ex in examples:
        # Check input length (between 15 and 500 words)
        input_len = len(ex['input'].split())
        if input_len < 15 or input_len > 500:
            continue
        
        # Check output length
        output_len = len(ex['output'].split())
        if output_len < 10:
            continue
        
        # Check if output is valid JSON
        try:
            output_json = json.loads(ex['output'])
            if 'intent' not in output_json or 'draft_response' not in output_json:
                continue
            if output_json['intent'] not in ['login_issue', 'billing', 'feature_request', 'bug_report', 
                                              'account_management', 'api_help', 'data_export', 
                                              'integration', 'performance', 'security', 'other']:
                continue
        except:
            continue
        
        filtered.append(ex)
    
    logger.info(f"Quality filtering: {len(examples)} → {len(filtered)} examples")
    return filtered

def augment_limited_data(examples: List[Dict]) -> List[Dict]:
    """Augment dataset if we have fewer than 500 examples (for Kaggle demo)"""
    
    if len(examples) >= 500:
        return examples
    
    logger.info(f"Only {len(examples)} examples found. Augmenting data...")
    augmented = examples.copy()
    
    # Create variations
    for ex in examples:
        # Variation 1: Slightly rephrase input
        var1 = ex.copy()
        var1['input'] = ex['input'].replace("cannot", "unable to").replace("problem", "issue")
        augmented.append(var1)
        
        # Variation 2: Add slight variation to response
        var2 = ex.copy()
        output = json.loads(var2['output'])
        output['confidence'] = 0.90
        var2['output'] = json.dumps(output)
        augmented.append(var2)
    
    logger.info(f"Augmented to {len(augmented)} examples")
    return augmented

# ============================================
# PART 3: DATASET SPLITTING
# ============================================

def split_dataset(data: List[Dict], train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42):
    """Stratified split maintaining class distribution"""
    
    # Group by intent
    stratified = defaultdict(list)
    for example in data:
        try:
            output = json.loads(example['output'])
            intent = output.get('intent', 'unknown')
            stratified[intent].append(example)
        except:
            stratified['unknown'].append(example)
    
    np.random.seed(seed)
    
    train_data = []
    val_data = []
    test_data = []
    
    for intent, examples in stratified.items():
        # Shuffle
        indices = np.random.permutation(len(examples))
        examples = [examples[i] for i in indices]
        
        n = len(examples)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        n_test = n - n_train - n_val
        
        train_data.extend(examples[:n_train])
        val_data.extend(examples[n_train:n_train + n_val])
        test_data.extend(examples[n_train + n_val:])
        
        logger.info(f"Intent '{intent}': {n} total → {n_train} train, {n_val} val, {n_test} test")
    
    # Final shuffle
    np.random.shuffle(train_data)
    np.random.shuffle(val_data)
    np.random.shuffle(test_data)
    
    logger.info(f"Total: {len(train_data)} train, {len(val_data)} val, {len(test_data)} test")
    
    return train_data, val_data, test_data

# ============================================
# PART 4: QLORA FINE-TUNING
# ============================================

def setup_model_and_tokenizer(base_model_id: str):
    """Load model with 4-bit quantization and prepare for QLoRA"""
    
    logger.info(f"Loading base model: {base_model_id}")
    
    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        use_cache=False  # Required for gradient checkpointing
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"  # For generation
    
    # Enable gradient checkpointing (saves memory)
    model.gradient_checkpointing_enable()
    
    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # LoRA configuration (optimized for Kaggle)
    lora_config = LoraConfig(
        r=8,  # Reduced from 16 to save memory on Kaggle
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # Apply LoRA
    model = get_peft_model(model, lora_config)
    
    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable parameters: {trainable_params:,} / {total_params:,} ({100 * trainable_params / total_params:.2f}%)")
    
    return model, tokenizer

def format_prompt(instruction: str, input_text: str, output_text: str = None):
    """Format prompt for training or inference"""
    prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
"""
    if output_text:
        prompt += output_text
    return prompt

def tokenize_function(examples, tokenizer, max_length=512):
    """Tokenize examples for training"""
    
    # Format prompts with outputs for training
    texts = [
        format_prompt(inst, inp, out)
        for inst, inp, out in zip(
            examples['instruction'],
            examples['input'],
            examples['output']
        )
    ]
    
    # Tokenize
    tokenized = tokenizer(
        texts,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt"
    )
    
    # For causal LM, labels are the same as input_ids
    tokenized["labels"] = tokenized["input_ids"].clone()
    
    return tokenized

def train_model(model, tokenizer, train_data, val_data, output_dir="/kaggle/working/output/lora_adapters"):
    """Execute training with QLoRA"""
    
    # Convert to HuggingFace Dataset
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    # Tokenize datasets
    logger.info("Tokenizing datasets...")
    
    def tokenize_wrapper(examples):
        return tokenize_function(examples, tokenizer)
    
    train_dataset = train_dataset.map(tokenize_wrapper, batched=True, remove_columns=train_dataset.column_names)
    val_dataset = val_dataset.map(tokenize_wrapper, batched=True, remove_columns=val_dataset.column_names)
    
    # Training arguments optimized for Kaggle free tier
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=2,  # Fewer epochs for Kaggle
        per_device_train_batch_size=1,  # Must be 1 for 16GB VRAM
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,  # Effective batch size = 4
        warmup_steps=50,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",  # Disable wandb for Kaggle
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",  # Memory efficient optimizer
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        padding=True,
        return_tensors="pt"
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )
    
    # Train!
    logger.info("Starting training...")
    trainer.train()
    
    # Save the model
    logger.info(f"Saving model to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save training metrics
    metrics = {
        "train_loss": trainer.state.log_history,
        "best_metric": trainer.state.best_metric,
        "best_model_checkpoint": trainer.state.best_model_checkpoint,
        "total_steps": trainer.state.global_step,
        "epoch": trainer.state.epoch,
    }
    
    with open("/kaggle/working/output/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    logger.info("Training complete!")
    return trainer

# ============================================
# PART 5: MAIN EXECUTION
# ============================================

def main():
    """Main execution flow"""
    
    logger.info("=" * 60)
    logger.info("Customer Support AI - QLoRA Fine-Tuning for Kaggle")
    logger.info("=" * 60)
    
    # Step 1: Load raw data
    logger.info("\n[Step 1] Loading raw tickets...")
    raw_data_path = "/kaggle/input/customer-support-tickets/raw_tickets.json"
    
    if not os.path.exists(raw_data_path):
        # Use sample data if file not found (for testing)
        logger.warning(f"Raw data not found at {raw_data_path}, using sample data")
        raw_data_path = "/kaggle/working/sample_tickets.json"
        create_sample_data(raw_data_path)
    
    with open(raw_data_path, 'r') as f:
        raw_tickets = json.load(f)
    
    logger.info(f"Loaded {len(raw_tickets)} raw tickets")
    
    # Step 2: Create training examples
    logger.info("\n[Step 2] Creating training examples...")
    training_examples = []
    for ticket in raw_tickets:
        try:
            example = create_training_example(ticket)
            training_examples.append(example)
        except Exception as e:
            logger.error(f"Failed to process ticket {ticket.get('ticket_id', 'unknown')}: {e}")
    
    logger.info(f"Created {len(training_examples)} training examples")
    
    # Step 3: Quality filtering
    logger.info("\n[Step 3] Quality filtering...")
    training_examples = filter_quality(training_examples)
    
    # Step 4: Deduplication
    logger.info("\n[Step 4] Deduplication...")
    training_examples = deduplicate_examples(training_examples, similarity_threshold=0.85)
    
    # Step 5: Data augmentation if needed
    logger.info("\n[Step 5] Data augmentation...")
    training_examples = augment_limited_data(training_examples)
    
    # Step 6: Split dataset
    logger.info("\n[Step 6] Splitting dataset...")
    train_data, val_data, test_data = split_dataset(training_examples)
    
    # Save splits for inspection
    os.makedirs("/kaggle/working/output", exist_ok=True)
    with open("/kaggle/working/output/train_split.json", "w") as f:
        json.dump(train_data, f, indent=2)
    with open("/kaggle/working/output/val_split.json", "w") as f:
        json.dump(val_data, f, indent=2)
    
    # Step 7: Setup model
    logger.info("\n[Step 7] Setting up model with QLoRA...")
    base_model_id = "meta-llama/Llama-3.2-3B-Instruct"  # Requires approval on HuggingFace
    # Alternative if Llama 3.2 not available:
    # base_model_id = "microsoft/phi-2"  # Smaller, works well
    
    try:
        model, tokenizer = setup_model_and_tokenizer(base_model_id)
    except Exception as e:
        logger.error(f"Failed to load {base_model_id}: {e}")
        logger.info("Trying alternative model: microsoft/phi-2")
        base_model_id = "microsoft/phi-2"
        model, tokenizer = setup_model_and_tokenizer(base_model_id)
    
    # Step 8: Train
    logger.info("\n[Step 8] Starting QLoRA fine-tuning...")
    trainer = train_model(model, tokenizer, train_data, val_data)
    
    # Step 9: Save test predictions
    logger.info("\n[Step 9] Generating test predictions...")
    predictions = []
    for example in test_data[:10]:  # Only test 10 examples to save time
        prompt = format_prompt(example['instruction'], example['input'])
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.3,
                do_sample=True,
                top_p=0.9
            )
        
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = generated.split("### Response:")[-1].strip()
        
        predictions.append({
            "input": example['input'],
            "ground_truth": example['output'],
            "prediction": response
        })
    
    with open("/kaggle/working/output/test_predictions.json", "w") as f:
        json.dump(predictions, f, indent=2)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Fine-tuning complete!")
    logger.info(f"Model saved to: /kaggle/working/output/lora_adapters")
    logger.info(f"Metrics saved to: /kaggle/working/output/metrics.json")
    logger.info(f"Test predictions saved to: /kaggle/working/output/test_predictions.json")
    logger.info("=" * 60)
    
    # Print memory usage
    if torch.cuda.is_available():
        logger.info(f"GPU Memory allocated: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
        logger.info(f"GPU Memory cached: {torch.cuda.memory_reserved()/1024**3:.2f} GB")

def create_sample_data(filepath):
    """Create sample data if real data not available"""
    sample_tickets = [
        {
            "ticket_id": "T-001",
            "subject": "Cannot login",
            "description": "I can't access my account. Password reset not working.",
            "resolution": "Unlocked account. User can now login.",
            "intent": "login_issue"
        },
        {
            "ticket_id": "T-002", 
            "subject": "Double charged",
            "description": "I was charged twice for my subscription.",
            "resolution": "Refunded duplicate charge.",
            "intent": "billing"
        },
        {
            "ticket_id": "T-003",
            "subject": "API webhook failing",
            "description": "My webhook endpoint stopped receiving events.",
            "resolution": "Webhook was disabled. Re-enabled and tested.",
            "intent": "api_help"
        }
    ]
    
    # Convert to training examples
    training_examples = [create_training_example(t) for t in sample_tickets]
    
    with open(filepath, 'w') as f:
        json.dump(training_examples, f, indent=2)
    
    logger.info(f"Created sample data with {len(training_examples)} examples")

if __name__ == "__main__":
    main()

model = prepare_model_for_kbit_training(model)
