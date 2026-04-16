"""
coercion_detector.py

Detects potential coercion by measuring response times to neutral calibration questions.
Returns a coercion score (0‑1) and optional boolean flag.
"""

import time
import random
import logging
from typing import Tuple, Optional

# Default calibration questions
DEFAULT_QUESTIONS = [
    "What is your favorite color?",
    "What is the name of your first pet?",
    "What is your favorite time of day?",
    "What is the last book you read?",
    "What is your favorite season?"
]

class CoercionDetector:
    """
    Detects potential coercion by measuring response times to neutral questions.
    A response time significantly shorter than the threshold may indicate rushing,
    which could be a sign of social pressure.
    """

    def __init__(self,
                 threshold_seconds: float = 0.5,
                 num_questions: int = 1,
                 questions: Optional[list] = None,
                 log_file: Optional[str] = None):
        """
        Args:
            threshold_seconds: Response time below this value (in seconds) is considered suspicious.
            num_questions: Number of calibration questions to ask.
            questions: Custom list of questions (strings). If None, uses default list.
            log_file: If provided, logs detection results to this file.
        """
        self.threshold = threshold_seconds
        self.num_questions = max(1, num_questions)
        self.questions = questions or DEFAULT_QUESTIONS
        self.baseline_times = []
        self.logger = self._setup_logger(log_file) if log_file else None

    def _setup_logger(self, log_file: str) -> logging.Logger:
        logger = logging.getLogger('CoercionDetector')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _ask_question(self, question: str) -> float:
        """Ask a single question and return elapsed time in seconds."""
        start = time.time()
        input(f"{question} ")
        return time.time() - start

    def detect(self) -> Tuple[float, bool]:
        """
        Run the coercion detection test.

        Returns:
            (coercion_score, is_coerced)
            - coercion_score: 0 (normal) to 1 (highly likely coerced)
            - is_coerced: True if average response time < threshold
        """
        total_time = 0.0
        # Randomly sample questions (allow duplicates if num_questions > len(questions))
        selected = random.choices(self.questions, k=self.num_questions)

        for i, q in enumerate(selected, 1):
            print(f"[Calibration {i}/{self.num_questions}]")
            elapsed = self._ask_question(q)
            total_time += elapsed
            self.baseline_times.append(elapsed)

        avg_time = total_time / self.num_questions
        is_coerced = avg_time < self.threshold

        # Coercion score: 1 - min(1, avg_time / threshold)
        # If avg_time is 0 → score 1; if avg_time >= threshold → score 0
        score = max(0.0, min(1.0, 1.0 - (avg_time / self.threshold))) if self.threshold > 0 else 0.0

        # Print feedback
        print(f"\nAverage response time: {avg_time:.2f}s")
        if is_coerced:
            print("⚠️ Your responses were very fast. Are you feeling pressured?")
            print("You can opt out at any time.")
        else:
            print("✅ Calibration complete.")

        # Log to file if enabled
        if self.logger:
            self.logger.info(f"avg_time={avg_time:.3f}, threshold={self.threshold}, score={score:.3f}, coerced={is_coerced}")

        return score, is_coerced

    def reset(self):
        """Clear stored baseline times (useful for repeated tests)."""
        self.baseline_times.clear()


# -----------------------------
# Command‑line interface
# -----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Coercion Detector for Radiant Protocol")
    parser.add_argument("--threshold", type=float, default=0.5, help="Response time threshold (seconds)")
    parser.add_argument("--questions", type=int, default=1, help="Number of calibration questions")
    parser.add_argument("--log", type=str, help="Log file path")
    args = parser.parse_args()

    detector = CoercionDetector(
        threshold_seconds=args.threshold,
        num_questions=args.questions,
        log_file=args.log
    )
    score, coerced = detector.detect()
    print(f"\nCoercion score: {score:.2f} / 1.00")
    print(f"Coerced: {'YES' if coerced else 'NO'}")
