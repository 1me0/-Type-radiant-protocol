# coercion_detector.py
import time
import random

class CoercionDetector:
    def __init__(self):
        self.baseline_time = None

    def detect(self) -> bool:
        # Ask a neutral question
        start = time.time()
        answer = input("What is your favorite color? (just for calibration): ")
        elapsed = time.time() - start
        self.baseline_time = elapsed
        # Simple heuristic: < 0.5 seconds may indicate rushed answer
        if elapsed < 0.5:
            print("Note: Your response was very fast. Are you feeling pressured?")
            print("You can opt out privately at any time.")
            return True  # potential coercion detected
        return False
