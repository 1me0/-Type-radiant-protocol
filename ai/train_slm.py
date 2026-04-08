"""
train_slm.py
Fine‑tunes a DistilBERT model on high‑CIS conversations and the six CIS principles.
Outputs a model ready for inference in the Radiant Protocol.
"""

import json
from transformers import DistilBertForSequenceClassification, Trainer, TrainingArguments, DistilBertTokenizer
from datasets import Dataset

def load_and_prepare_data(jsonl_path: str, principles: list):
    """Load JSONL data (each line: {"text": "...", "label": 0/1}) and add principles as positive examples."""
    data = []
    with open(jsonl_path, "r") as f:
        for line in f:
            data.append(json.loads(line))
    for p in principles:
        data.append({"text": p, "label": 1})
    return data

def train():
    principles = [
        "Non‑Authority: The score is a measurement, not a judgment.",
        "Awareness Over Control: The purpose is to inform, not to enforce.",
        "Silence Supremacy: No metric captures the whole truth; silence remains higher.",
        "Interpretive Freedom: Scores are guides, not conclusions.",
        "Transparency: All formulas and logic are open and auditable.",
        "Self‑Reflection: Use the mirror for yourself before judging others."
    ]
    data = load_and_prepare_data("data/high_cis_conversations.jsonl", principles)
    
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    def tokenize(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)
    
    dataset = Dataset.from_list(data)
    dataset = dataset.map(tokenize, batched=True)
    dataset = dataset.rename_column("label", "labels")
    dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    
    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
    training_args = TrainingArguments(
        output_dir="./cis_slm",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        save_steps=500,
        logging_dir="./logs",
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
    trainer.train()
    model.save_pretrained("./cis_slm_model")
    tokenizer.save_pretrained("./cis_slm_model")

if __name__ == "__main__":
    train()
