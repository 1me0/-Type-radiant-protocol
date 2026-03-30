const [scoreThreshold, setScoreThreshold] = useState(7); // configurable
const [currentScore, setCurrentScore] = useState<number | null>(null);

// ... in the message input handling (if you have a textarea)
const evaluateMessage = async (text: string) => {
    const response = await fetch('http://localhost:8000/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, context: 'general' })
    });
    const data = await response.json();
    setCurrentScore(data.score);
    return data.score;
};

const handleSubmitProof = async () => {
    if (currentScore !== null && currentScore < scoreThreshold) {
        alert(`Your message score (${currentScore}) is below the required threshold (${scoreThreshold}). Please improve clarity.`);
        return;
    }
    // ... proceed with proof submission
};
