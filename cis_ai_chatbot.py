"""
CIS‑Powered AI Chatbot

This script implements an AI assistant that:
- Generates responses to user messages.
- Computes CIS score for each response based on alignment, understanding, accuracy, distortion.
- Optionally rewrites responses to improve the score.
- Uses a simple local transformer model (e.g., GPT‑2) for demonstration.
- Can be adapted to any LLM API (OpenAI, Cohere, etc.).

CIS Formula:
    CIS = 10 * (0.2*Alignment + 0.3*Understanding + 0.4*Accuracy - 0.1*Distortion)
    All metrics in [0,1].
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
import math

# ------------------------------
# 1. CIS Scoring Function
# ------------------------------
def compute_cis(text: str, user_intent: str = "", context: str = "") -> tuple:
    """
    Compute CIS score and component metrics for a given response.
    This is a simplified heuristic; in production you might use a fine‑tuned model.
    Returns (score, metrics_dict).
    """
    # Dummy heuristic: longer, more polite, and more relevant = higher scores
    # In a real system, use an LLM to evaluate alignment, understanding, etc.
    
    # Alignment (context fit): assume high if response contains keywords from user intent
    alignment = 0.7
    if user_intent and any(word in text.lower() for word in user_intent.lower().split()):
        alignment += 0.2
    alignment = min(1.0, alignment)
    
    # Understanding (captured intent): simple length heuristic
    understanding = min(1.0, len(text) / 200)
    
    # Accuracy (factual correctness): dummy – always 0.8 for demo
    accuracy = 0.8
    
    # Distortion (noise, fillers, repetitions)
    distortion = min(1.0, text.count('?') / 10 + text.count('!') / 10 + text.count('...') / 5)
    
    raw = 0.2 * alignment + 0.3 * understanding + 0.4 * accuracy - 0.1 * distortion
    score = max(0.0, min(10.0, raw * 10.0))
    metrics = {
        "alignment": alignment,
        "understanding": understanding,
        "accuracy": accuracy,
        "distortion": distortion
    }
    return score, metrics

# ------------------------------
# 2. AI Response Generator (Local Model)
# ------------------------------
class CISBot:
    def __init__(self, model_name="microsoft/DialoGPT-medium"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.chat_history_ids = None
        self.cis_threshold = 7.0   # minimum acceptable CIS score
        self.auto_improve = True    # automatically rewrite low‑score responses

    def generate_response(self, user_input: str, user_intent: str = "") -> str:
        # Encode user input
        new_input_ids = self.tokenizer.encode(user_input + self.tokenizer.eos_token, return_tensors='pt')
        
        # Append to chat history
        if self.chat_history_ids is not None:
            bot_input_ids = torch.cat([self.chat_history_ids, new_input_ids], dim=-1)
        else:
            bot_input_ids = new_input_ids
        
        # Generate response
        self.chat_history_ids = self.model.generate(
            bot_input_ids,
            max_length=1000,
            pad_token_id=self.tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.7
        )
        response = self.tokenizer.decode(self.chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        
        # Evaluate CIS score
        score, metrics = compute_cis(response, user_intent)
        
        # Optionally improve response
        if self.auto_improve and score < self.cis_threshold:
            improved = self._improve_response(response, metrics)
            if improved and improved != response:
                response = improved
                score, metrics = compute_cis(response, user_intent)  # recompute
                
        return response, score, metrics
    
    def _improve_response(self, text: str, metrics: dict) -> str:
        """Heuristic improvement based on low metrics."""
        improved = text
        if metrics["alignment"] < 0.6:
            improved = "I think " + improved
        if metrics["understanding"] < 0.6:
            improved = improved + " Could you clarify?"
        if metrics["distortion"] > 0.3:
            improved = re.sub(r'[!?]+', '.', improved)
        return improved

# ------------------------------
# 3. Chat Loop
# ------------------------------
def main():
    print("CIS‑Powered AI Chatbot (type 'exit' to quit)")
    bot = CISBot()
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        
        # Optionally ask user for intent or context
        user_intent = input("What is your intent (optional, press Enter to skip): ")
        
        response, score, metrics = bot.generate_response(user_input, user_intent)
        
        print(f"\nAI: {response}")
        print(f"CIS Score: {score:.2f} (Alignment: {metrics['alignment']:.2f}, "
              f"Understanding: {metrics['understanding']:.2f}, "
              f"Accuracy: {metrics['accuracy']:.2f}, "
              f"Distortion: {metrics['distortion']:.2f})")
        if score < 7.0:
            print("⚠️ Low clarity – consider rephrasing or ask for clarification.")

if __name__ == "__main__":
    main()
