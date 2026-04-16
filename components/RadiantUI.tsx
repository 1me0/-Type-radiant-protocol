// RadiantUI.tsx
import { useState, useEffect, useRef, useCallback } from "react";
import { useAccount, useConnect, useDisconnect, useBalance } from "wagmi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { ethers } from "ethers";

// ============================================================
// TYPES
// ============================================================
interface Metrics {
  alignment: number;
  accuracy: number;
  distortion: number;
  confidence: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  truthScore?: number;
  metrics?: Metrics;
  explanation?: string;
  timestamp: number;
  originalQuery?: string;
  challengeHistory?: string[]; // for deep challenge
}

interface UserReputation {
  truthScore: number;        // 0-100 average of truth scores
  stability: "High" | "Medium" | "Low";
  totalEarned: number;       // in RAD
  messageCount: number;
}

// API response shapes (adjust to your backend)
interface ApiResponse {
  response: string;
  cis: number;
  metrics: Metrics;
  explanation: string;
}

interface ChallengeResponse {
  contradictionFound: boolean;
  details: string;
  stabilityConfirmed: boolean;
  nextChallenge?: string;
}

// Contract ABI (partial for claim)
const TOKEN_ABI = [
  "function balanceOf(address) view returns (uint256)",
  "function claim() external"
];

// ============================================================
// HELPER
// ============================================================
const getTruthStatus = (score: number): { text: string; color: string } => {
  if (score > 8.5) return { text: "✅ Highly reliable", color: "text-green-400" };
  if (score > 6.5) return { text: "⚠️ Partially reliable", color: "text-yellow-400" };
  return { text: "❌ Low reliability", color: "text-red-400" };
};

const getStabilityFromScore = (score: number): "High" | "Medium" | "Low" => {
  if (score >= 70) return "High";
  if (score >= 40) return "Medium";
  return "Low";
};

// ============================================================
// MAIN COMPONENT
// ============================================================
export default function RadiantUI() {
  // ---------- Wallet (wagmi) ----------
  const { address, isConnected } = useAccount();
  const { connect, connectors, error: connectError } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: tokenBalance } = useBalance({ address, token: process.env.NEXT_PUBLIC_TOKEN_ADDRESS });

  // ---------- UI State ----------
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [userReputation, setUserReputation] = useState<UserReputation>({
    truthScore: 0,
    stability: "Medium",
    totalEarned: 0,
    messageCount: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [challengeModal, setChallengeModal] = useState<{ message: ChatMessage; open: boolean }>({ message: null, open: false });
  const [challengeInput, setChallengeInput] = useState("");
  const [challengeResponse, setChallengeResponse] = useState<string>("");
  const [expandedExplanationId, setExpandedExplanationId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Persistence: load from localStorage on mount
  useEffect(() => {
    const savedMessages = localStorage.getItem("radiant_messages");
    const savedReputation = localStorage.getItem("radiant_reputation");
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {}
    }
    if (savedReputation) {
      try {
        setUserReputation(JSON.parse(savedReputation));
      } catch (e) {}
    }
  }, []);

  // Save to localStorage whenever messages or reputation change
  useEffect(() => {
    localStorage.setItem("radiant_messages", JSON.stringify(messages));
  }, [messages]);
  useEffect(() => {
    localStorage.setItem("radiant_reputation", JSON.stringify(userReputation));
  }, [userReputation]);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---------- API CALLS ----------
  const callTruthAPI = async (query: string): Promise<ApiResponse> => {
    const res = await fetch("/api/truth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error("Truth API failed");
    return res.json();
  };

  const callChallengeAPI = async (statement: string, challenge: string): Promise<ChallengeResponse> => {
    const res = await fetch("/api/challenge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ statement, challenge }),
    });
    if (!res.ok) throw new Error("Challenge API failed");
    return res.json();
  };

  // Update reputation after each assistant message
  const updateReputation = (newScore: number) => {
    const totalScore = userReputation.truthScore * userReputation.messageCount;
    const newCount = userReputation.messageCount + 1;
    const newAverage = (totalScore + newScore) / newCount;
    setUserReputation({
      truthScore: newAverage,
      stability: getStabilityFromScore(newAverage),
      totalEarned: userReputation.totalEarned + (newScore / 10) * 0.3, // 0.3 RAD per 10 points
      messageCount: newCount,
    });
  };

  // ---------- Handlers ----------
  const handleSubmit = async () => {
    if (!input.trim()) return;
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: Date.now(),
      originalQuery: input,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const apiRes = await callTruthAPI(userMessage.content);
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: apiRes.response,
        truthScore: apiRes.cis,
        metrics: apiRes.metrics,
        explanation: apiRes.explanation,
        timestamp: Date.now(),
        originalQuery: userMessage.content,
        challengeHistory: [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      updateReputation(apiRes.cis);
    } catch (err) {
      setError("Failed to get response. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Deep challenge: open modal to submit counter‑argument
  const handleOpenChallenge = (msg: ChatMessage) => {
    setChallengeModal({ message: msg, open: true });
    setChallengeInput("");
    setChallengeResponse("");
  };

  const handleSubmitChallenge = async () => {
    if (!challengeModal.message || !challengeInput.trim()) return;
    setLoading(true);
    try {
      const res = await callChallengeAPI(challengeModal.message.content, challengeInput);
      let responseText = "";
      if (res.contradictionFound) {
        responseText = `❌ Contradiction found: ${res.details}`;
      } else if (res.stabilityConfirmed) {
        responseText = `✅ Stability confirmed. Statement is consistent with known constraints.`;
      } else {
        responseText = `⚠️ ${res.details}`;
      }
      if (res.nextChallenge) {
        responseText += `\n\n🔄 Next challenge: ${res.nextChallenge}`;
      }
      setChallengeResponse(responseText);
      // Append to message's challenge history
      setMessages(prev => prev.map(msg => 
        msg.id === challengeModal.message.id 
          ? { ...msg, challengeHistory: [...(msg.challengeHistory || []), challengeInput] }
          : msg
      ));
    } catch (err) {
      setChallengeResponse("❌ Challenge API failed.");
    } finally {
      setLoading(false);
    }
  };

  // Claim rewards (real contract interaction)
  const handleClaimRewards = async () => {
    if (!isConnected || !address) {
      alert("Connect wallet first");
      return;
    }
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const tokenContract = new ethers.Contract(process.env.NEXT_PUBLIC_TOKEN_ADDRESS!, TOKEN_ABI, signer);
      const tx = await tokenContract.claim();
      await tx.wait();
      alert("Rewards claimed successfully!");
      // Optionally refresh balance
    } catch (err) {
      alert("Claim failed: " + err.message);
    }
  };

  // ---------- Render ----------
  return (
    <div className="min-h-screen bg-black text-white p-4 flex flex-col items-center">
      {/* Header with wallet + reputation */}
      <div className="w-full max-w-2xl flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-xl font-bold">🌌 Radiant</h1>
        <div className="flex items-center gap-3 flex-wrap">
          {isConnected ? (
            <>
              <div className="text-sm opacity-70">{address?.slice(0,6)}...{address?.slice(-4)}</div>
              <Button variant="outline" size="sm" onClick={() => disconnect()}>Disconnect</Button>
            </>
          ) : (
            <div className="flex gap-2">
              {connectors.map((connector) => (
                <Button key={connector.id} variant="outline" size="sm" onClick={() => connect({ connector })}>
                  Connect {connector.name}
                </Button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 bg-gray-800 px-3 py-1 rounded-full">
            <span className="text-xs">🧠 Truth Score: {userReputation.truthScore.toFixed(1)}</span>
            <span className="text-xs">📊 {userReputation.stability}</span>
            <span className="text-xs">💰 {userReputation.totalEarned.toFixed(2)} RAD</span>
            {tokenBalance && <span className="text-xs">🪙 Bal: {parseFloat(tokenBalance.formatted).toFixed(2)} RAD</span>}
            <Button size="sm" variant="outline" onClick={handleClaimRewards}>Claim</Button>
          </div>
        </div>
      </div>
      {connectError && <div className="text-red-400 text-sm mb-2">Connection error: {connectError.message}</div>}

      {/* Chat history */}
      <div className="w-full max-w-2xl space-y-3 mb-4 max-h-[50vh] overflow-y-auto p-2">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <Card className={`rounded-2xl p-3 max-w-[85%] ${msg.role === "user" ? "bg-blue-900/30" : "bg-gray-800/50"}`}>
                <CardContent className="p-0 space-y-2">
                  <p className="text-sm">{msg.content}</p>
                  {msg.truthScore !== undefined && (
                    <div className="text-xs space-y-1">
                      <div className="flex justify-between">
                        <span>Truth Score</span>
                        <span>{msg.truthScore.toFixed(1)} / 10</span>
                      </div>
                      <div className="w-full h-1 bg-gray-700 rounded-full">
                        <div className="h-1 rounded-full bg-green-400" style={{ width: `${msg.truthScore * 10}%` }} />
                      </div>
                      {msg.metrics && (
                        <div className="grid grid-cols-2 gap-1 text-gray-300">
                          <div>Alignment: {msg.metrics.alignment.toFixed(2)}</div>
                          <div>Accuracy: {msg.metrics.accuracy.toFixed(2)}</div>
                          <div>Distortion: {msg.metrics.distortion.toFixed(2)}</div>
                          <div>Confidence: {msg.metrics.confidence.toFixed(2)}</div>
                        </div>
                      )}
                      <div className={getTruthStatus(msg.truthScore).color}>
                        {getTruthStatus(msg.truthScore).text}
                      </div>
                      {msg.explanation && (
                        <div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setExpandedExplanationId(expandedExplanationId === msg.id ? null : msg.id)}
                          >
                            {expandedExplanationId === msg.id ? "Hide" : "Why this score?"}
                          </Button>
                          {expandedExplanationId === msg.id && (
                            <div className="mt-2 p-2 bg-gray-700 rounded text-xs">
                              {msg.explanation}
                            </div>
                          )}
                        </div>
                      )}
                      <div className="flex gap-2 mt-2">
                        <Button size="sm" variant="outline" onClick={() => handleOpenChallenge(msg)} disabled={loading}>
                          Challenge
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={chatEndRef} />
      </div>

      {/* Challenge Modal */}
      {challengeModal.open && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <Card className="w-full max-w-md p-4">
            <h3 className="text-lg font-bold mb-2">Challenge Statement</h3>
            <p className="text-sm mb-2">{challengeModal.message?.content}</p>
            <textarea
              value={challengeInput}
              onChange={(e) => setChallengeInput(e.target.value)}
              placeholder="Enter your counter‑argument or challenge..."
              className="w-full p-2 bg-gray-800 rounded text-white mb-2"
              rows={3}
            />
            {challengeResponse && <div className="text-xs p-2 bg-gray-700 rounded mb-2">{challengeResponse}</div>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setChallengeModal({ message: null, open: false })}>Close</Button>
              <Button onClick={handleSubmitChallenge} disabled={loading}>Submit Challenge</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Input area */}
      <Card className="w-full max-w-2xl rounded-2xl p-3 mb-2">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && handleSubmit()}
            placeholder="Ask or say something..."
            className="flex-1 bg-transparent outline-none text-white placeholder-gray-400"
            disabled={loading}
          />
          <Button onClick={handleSubmit} disabled={loading || !input.trim()}>
            {loading ? "Thinking..." : "Send"}
          </Button>
        </div>
      </Card>

      {loading && <div className="text-gray-400 text-sm">⚡ Generating proof...</div>}
      {error && <div className="text-red-400 text-sm">{error}</div>}
    </div>
  );
    }
