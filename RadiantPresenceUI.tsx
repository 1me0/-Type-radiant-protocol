import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ethers } from "ethers"; // For wallet connection

// Helper: deterministic hash (djb2) to generate a score between 0-100
function hashToScore(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & hash;
  }
  return Math.abs(hash % 101);
}

export default function RadiantPresenceUI() {
  const [wallet, setWallet] = useState<string | null>(null);
  const [presenceData, setPresenceData] = useState<{
    identifier: string;
    firstSeen: number;
    score: number;
    anchored: boolean;
  } | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("radiant_presence");
    if (stored) {
      const data = JSON.parse(stored);
      setPresenceData(data);
    }
  }, []);

  // Connect wallet and register presence
  const connectAndRegister = async () => {
    if (typeof window.ethereum === "undefined") {
      alert("MetaMask not detected");
      return;
    }
    const provider = new ethers.providers.Web3Provider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    const signer = provider.getSigner();
    const address = await signer.getAddress();
    setWallet(address);

    // Check if already registered
    const stored = localStorage.getItem("radiant_presence");
    if (stored) {
      const data = JSON.parse(stored);
      if (data.identifier === address) {
        setPresenceData(data);
        return;
      }
    }

    // New registration
    const score = hashToScore(address);
    const firstSeen = Date.now();
    const newData = {
      identifier: address,
      firstSeen,
      score,
      anchored: false,
    };
    localStorage.setItem("radiant_presence", JSON.stringify(newData));
    setPresenceData(newData);
  };

  // Simulate on‑chain anchoring (replace with actual contract call)
  const anchorOnChain = async () => {
    if (!presenceData) return;
    // In a real implementation, you would call your smart contract:
    // const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, signer);
    // await contract.registerPresence(presenceData.identifier, presenceData.score, presenceData.firstSeen);
    alert("Simulated on‑chain anchoring. Replace with actual contract call.");
    const updated = { ...presenceData, anchored: true };
    localStorage.setItem("radiant_presence", JSON.stringify(updated));
    setPresenceData(updated);
  };

  const formatDate = (timestamp: number) => new Date(timestamp).toLocaleString();

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white p-6">
      <Card className="w-full max-w-md rounded-2xl shadow-xl bg-zinc-900 border-zinc-800">
        <CardContent className="p-6 text-center space-y-6">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold"
          >
            Radiant Presence
          </motion.h1>
          <p className="text-sm opacity-70">
            Prove you were there. Turn it into value.
          </p>

          {!presenceData ? (
            <Button onClick={connectAndRegister} className="w-full">
              Connect Wallet & Register Presence
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-zinc-800 text-left">
                <p><strong>Identifier:</strong> {presenceData.identifier.slice(0,6)}...{presenceData.identifier.slice(-4)}</p>
                <p><strong>Presence Score:</strong> {presenceData.score}/100</p>
                <p><strong>First seen:</strong> {formatDate(presenceData.firstSeen)}</p>
                <p><strong>Anchored on‑chain:</strong> {presenceData.anchored ? "✅ Yes" : "❌ No"}</p>
              </div>

              {!presenceData.anchored && (
                <Button onClick={anchorOnChain} variant="outline" className="w-full">
                  Anchor on‑chain
                </Button>
              )}
              <p className="text-xs text-gray-400">
                Your presence score is deterministic and can be used for CIS scoring, staking multipliers, or reputation.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
