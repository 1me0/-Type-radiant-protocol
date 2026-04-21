// frontend/components/MessageInput.tsx
// Radiant Protocol – Message Input with CIS Scoring and Threshold Check

import React, { useState, useCallback } from 'react';

interface MessageInputProps {
  onSubmitProof: (message: string, score: number) => Promise<void>;
  initialThreshold?: number;
  apiUrl?: string;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSubmitProof,
  initialThreshold = 7,
  apiUrl = 'http://localhost:8000/score',
}) => {
  const [message, setMessage] = useState('');
  const [scoreThreshold] = useState(initialThreshold);
  const [currentScore, setCurrentScore] = useState<number | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Evaluate message against CIS endpoint
  const evaluateMessage = useCallback(async (text: string): Promise<number> => {
    if (!text.trim()) return 0;
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, context: 'general' }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const score = typeof data.score === 'number' ? data.score : 0;
      setCurrentScore(score);
      return score;
    } catch (err) {
      console.error('CIS scoring failed', err);
      setError('Could not evaluate message clarity. Please try again.');
      return 0;
    }
  }, [apiUrl]);

  // Handle message change: debounced scoring
  const handleMessageChange = useCallback(async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    setMessage(newText);
    setError(null);
    if (!newText.trim()) {
      setCurrentScore(null);
      return;
    }
    setIsEvaluating(true);
    try {
      await evaluateMessage(newText);
    } finally {
      setIsEvaluating(false);
    }
  }, [evaluateMessage]);

  // Submit proof after threshold check
  const handleSubmit = useCallback(async () => {
    if (!message.trim()) {
      setError('Please enter a message.');
      return;
    }
    if (currentScore === null) {
      setError('Message not evaluated yet. Wait a moment.');
      return;
    }
    if (currentScore < scoreThreshold) {
      setError(`Your message score (${currentScore.toFixed(1)}) is below the required threshold (${scoreThreshold}). Please improve clarity.`);
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmitProof(message, currentScore);
      // Clear form on success
      setMessage('');
      setCurrentScore(null);
      setError(null);
    } catch (err) {
      setError('Submission failed. Please try again.');
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  }, [message, currentScore, scoreThreshold, onSubmitProof]);

  // Helper to get score colour
  const getScoreColor = (score: number) => {
    if (score >= 8) return '#2e7d32'; // green
    if (score >= 6) return '#f9a825'; // yellow
    return '#c62828'; // red
  };

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '12px', padding: '16px', background: '#f8f9fa' }}>
      <label htmlFor="message" style={{ fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
        ✍️ Your Message
      </label>
      <textarea
        id="message"
        rows={3}
        value={message}
        onChange={handleMessageChange}
        placeholder="Type your message here..."
        style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ccc' }}
        disabled={isSubmitting}
      />
      <div style={{ marginTop: '8px', fontSize: '0.85rem' }}>
        {isEvaluating && <span>🧠 Evaluating clarity...</span>}
        {!isEvaluating && currentScore !== null && (
          <span>
            CIS Score: <strong style={{ color: getScoreColor(currentScore) }}>{currentScore.toFixed(1)} / 10</strong>
            {currentScore < scoreThreshold && ` (need ≥ ${scoreThreshold})`}
          </span>
        )}
        {error && <span style={{ color: '#c62828' }}>⚠️ {error}</span>}
      </div>
      <button
        onClick={handleSubmit}
        disabled={isSubmitting || isEvaluating || !message.trim()}
        style={{
          marginTop: '12px',
          padding: '8px 16px',
          background: '#1a2a3a',
          color: 'white',
          border: 'none',
          borderRadius: '30px',
          cursor: 'pointer',
        }}
      >
        {isSubmitting ? 'Submitting...' : 'Submit Proof'}
      </button>
      <div style={{ fontSize: '0.7rem', marginTop: '12px', color: '#6c757d' }}>
        💡 Messages with CIS score ≥ {scoreThreshold} can be submitted as proofs.
      </div>
    </div>
  );
};

export default MessageInput;
