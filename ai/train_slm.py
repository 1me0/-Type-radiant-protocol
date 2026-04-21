"""
train_slm.py
Fine‑tunes a DistilBERT model on high‑CIS conversations and the six CIS principles.
Outputs a model ready for inference in the Radiant Protocol.

Usage:
    python train_slm.py --data_path data/high_cis_conversations.jsonl --output_dir ./cis_slm_model
"""

import os
import json
import argparse
import logging
from typing import List, Dict

import torch
from transformers import (
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments,
    DistilBertTokenizer,
    EarlyStoppingCallback
)
from datasets import Dataset, DatasetDict
from sklearn.model_selection import train_test_split

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# CIS Principles (used as positive examples)
# ============================================================
CIS_PRINCIPLES = [
    "Non‑Authority: The score is a measurement, not a judgment.",
    "Awareness Over Control: The purpose is to inform, not to enforce.",
    "Silence Supremacy: No metric captures the whole truth; silence remains higher.",
    "Interpretive Freedom: Scores are guides, not conclusions.",
    "Transparency: All formulas and logic are open and auditable.",
    "Self‑Reflection: Use the mirror for yourself before judging others."
]


def load_data(jsonl_path: str) -> List[Dict[str, int]]:
    """
    Load JSONL data where each line contains {"text": "...", "label": 0/1}.
    Returns a list of dictionaries.
    """
    data = []
    if not os.path.exists(jsonl_path):
        logger.warning(f"Data file {jsonl_path} not found. Using only CIS principles.")
        return data

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Validate required keys
                if "text" in entry and "label" in entry:
                    data.append({"text": entry["text"], "label": int(entry["label"])})
                else:
                    logger.warning(f"Skipping invalid entry: {entry}")
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed JSON line: {e}")
    return data


def prepare_dataset(data: List[Dict[str, int]], principles: List[str]) -> DatasetDict:
    """
    Combine loaded data with CIS principles (all label 1).
    Split into train (80%) and validation (20%).
    """
    # Add principles as positive examples
    for p in principles:
        data.append({"text": p, "label": 1})

    if not data:
        raise ValueError("No data available for training. Provide a valid JSONL file or check CIS principles.")

    # Convert to list of texts and labels
    texts = [item["text"] for item in data]
    labels = [item["label"] for item in data]

    # Train/validation split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    train_dataset = Dataset.from_dict({"text": train_texts, "label": train_labels})
    val_dataset = Dataset.from_dict({"text": val_texts, "label": val_labels})

    return DatasetDict({"train": train_dataset, "validation": val_dataset})


def tokenize_dataset(dataset: DatasetDict, tokenizer: DistilBertTokenizer, max_length: int = 128) -> DatasetDict:
    """Tokenize the dataset and rename label column to 'labels'."""
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=max_length
        )

    tokenized = dataset.map(tokenize_function, batched=True)
    tokenized = tokenized.rename_column("label", "labels")
    tokenized.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    return tokenized


def train_model(
    train_dataset: Dataset,
    val_dataset: Dataset,
    output_dir: str,
    num_epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 2e-5,
    use_early_stopping: bool = True
) -> None:
    """Fine‑tune DistilBERT on the prepared dataset."""
    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_dir=os.path.join(output_dir, "logs"),
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to="none",           # Disable wandb/tensorboard unless configured
        save_total_limit=2,
        learning_rate=learning_rate,
        warmup_ratio=0.1,
    )

    # Compute accuracy during evaluation
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        preds = predictions.argmax(-1)
        accuracy = (preds == labels).float().mean().item()
        return {"accuracy": accuracy}

    callbacks = []
    if use_early_stopping:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=2))

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=callbacks,
    )

    logger.info("Starting training...")
    trainer.train()

    # Save final model and tokenizer
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Model saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Fine‑tune DistilBERT on CIS conversation data.")
    parser.add_argument("--data_path", type=str, default="data/high_cis_conversations.jsonl",
                        help="Path to JSONL file with text and label fields.")
    parser.add_argument("--output_dir", type=str, default="./cis_slm_model",
                        help="Directory to save the fine‑tuned model.")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs.")
    parser.add_argument("--batch_size", type=int, default=8, help="Training batch size per device.")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="Learning rate.")
    parser.add_argument("--max_length", type=int, default=128, help="Maximum token length.")
    parser.add_argument("--no_early_stopping", action="store_true", help="Disable early stopping.")
    args = parser.parse_args()

    # Load raw data
    raw_data = load_data(args.data_path)
    logger.info(f"Loaded {len(raw_data)} examples from {args.data_path}")

    # Prepare dataset (adds CIS principles and splits)
    dataset_dict = prepare_dataset(raw_data, CIS_PRINCIPLES)
    logger.info(f"Train size: {len(dataset_dict['train'])}, Validation size: {len(dataset_dict['validation'])}")

    # Tokenize
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    tokenized_dataset = tokenize_dataset(dataset_dict, tokenizer, max_length=args.max_length)

    # Train
    train_model(
        train_dataset=tokenized_dataset["train"],
        val_dataset=tokenized_dataset["validation"],
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        use_early_stopping=not args.no_early_stopping
    )


if __name__ == "__main__":
    main()
