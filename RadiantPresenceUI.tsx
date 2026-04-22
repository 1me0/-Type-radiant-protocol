import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ethers, Eip1193Provider } from "ethers";
import { Share2, X, MessageCircle } from "lucide-react";

// ============================================================
// Types
// ============================================================
declare global {
  interface Window {
    ethereum?: Eip1193Provider & {
      on: (event: string, handler: (...args: any[]) => void) => void;
      removeListener: (event: string, handler: (...args: any[]) => void) => void;
    };
  }
}

interface PresenceData {
  identifier: string;
  firstSeen: number;
  score: number;
  anchored: boolean;
}

// ============================================================
// Configuration
// ============================================================
const EXPECTED_CHAIN_ID = 11155111; // Sepolia testnet
const EXPECTED_CHAIN_NAME = "Sepolia";
const CONTRACT_ADDRESS = import.meta.env.VITE_RADIANT_CONTRACT_ADDRESS || "";
const RADIANT_HOMEPAGE = "https://radiantprotocol.com"; // Replace with actual URL

// Minimal ABI for registerPresence
const CONTRACT_ABI = [
  "function registerPresence(string memory identifier, uint256 score, uint256 timestamp) external",
];

// ============================================================
// Utilities
// ============================================================
function hashToScore(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) + hash + str.charCodeAt(i);
    hash = hash >>> 0; // keep as unsigned 32-bit
  }
  return hash % 101; // 0–100
}

function formatAddress(addr: string): string {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function formatDate(timestamp: number): string {
  return new Date(timestamp).toLocaleString();
}

// ============================================================
// Share Helpers
// ============================================================
function generateShareText(score: number, anchored: boolean): string {
  const status = anchored ? "anchored on‑chain" : "registered";
  return `I just proved my Radiant Presence with a score of ${score}/100! 🔆\n\nJoin the CIS Radiant Protocol and turn your presence into value.\n${RADIANT_HOMEPAGE}`;
}

function shareToX(score: number, anchored: boolean): void {
  const text = encodeURIComponent(generateShareText(score, anchored));
  window.open(`https://twitter.com/intent/tweet?text=${text}`, "_blank");
}

function shareToFarcaster(score: number, anchored: boolean): void {
  const text = encodeURIComponent(generateShareText(score, anchored));
  // Farcaster uses Warpcast intent URL
  window.open(`https://warpcast.com/~/compose?text=${text}`, "_blank");
}

// ============================================================
// Main Component
// ============================================================
export default function RadiantPresenceUI() {
  const [wallet, setWallet] = useState<string | null>(null);
  const [presenceData, setPresenceData] = useState<PresenceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCorrectNetwork, setIsCorrectNetwork] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSwitchingNetwork, setIsSwitchingNetwork] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const mountedRef = useRef(true);

  // ==================== Network Helpers ====================
  const getProvider = useCallback((): ethers.BrowserProvider | null => {
    if (!window.ethereum) return null;
    return new ethers.BrowserProvider(window.ethereum);
  }, []);

  const checkNetwork = useCallback(async (provider: ethers.BrowserProvider): Promise<boolean> => {
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    const correct = chainId === EXPECTED_CHAIN_ID;
    setIsCorrectNetwork(correct);
    if (!correct) {
      setError(`Please switch to ${EXPECTED_CHAIN_NAME} (chain ID ${EXPECTED_CHAIN_ID}). Current: ${chainId}`);
    } else {
      setError(null);
    }
    return correct;
  }, []);

  const switchNetwork = useCallback(async () => {
    if (!window.ethereum) return;
    setIsSwitchingNetwork(true);
    setError(null);
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: `0x${EXPECTED_CHAIN_ID.toString(16)}` }],
      });
    } catch (switchError: any) {
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: `0x${EXPECTED_CHAIN_ID.toString(16)}`,
                chainName: EXPECTED_CHAIN_NAME,
                nativeCurrency: { name: "Sepolia ETH", symbol: "ETH", decimals: 18 },
                rpcUrls: ["https://sepolia.infura.io/v3/"],
                blockExplorerUrls: ["https://sepolia.etherscan.io"],
              },
            ],
          });
        } catch (addError) {
          console.error(addError);
          setError("Failed to add network. Please add manually.");
        }
      } else {
        console.error(switchError);
        setError("Failed to switch network.");
      }
    } finally {
      setIsSwitchingNetwork(false);
      const provider = getProvider();
      if (provider) await checkNetwork(provider);
    }
  }, [getProvider, checkNetwork]);

  // ==================== Presence Management ====================
  const loadStoredPresence = useCallback((address: string): PresenceData | null => {
    const stored = localStorage.getItem("radiant_presence");
    if (!stored) return null;
    try {
      const data = JSON.parse(stored) as PresenceData;
      return data.identifier === address ? data : null;
    } catch {
      return null;
    }
  }, []);

  const savePresence = useCallback((data: PresenceData) => {
    localStorage.setItem("radiant_presence", JSON.stringify(data));
    setPresenceData(data);
  }, []);

  const disconnect = useCallback(() => {
    setWallet(null);
    setPresenceData(null);
    localStorage.removeItem("radiant_presence");
    setError(null);
    setStatusMessage(null);
  }, []);

  // ==================== Wallet Connection & Registration ====================
  const connectAndRegister = useCallback(async () => {
    if (!window.ethereum) {
      setError("MetaMask not detected. Please install MetaMask.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatusMessage(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const isNetOk = await checkNetwork(provider);
      if (!isNetOk) {
        setLoading(false);
        return;
      }
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      setWallet(address);

      const existing = loadStoredPresence(address);
      if (existing) {
        setPresenceData(existing);
        return;
      }

      const score = hashToScore(address);
      const firstSeen = Date.now();
      const newData: PresenceData = {
        identifier: address,
        firstSeen,
        score,
        anchored: false,
      };
      savePresence(newData);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to connect wallet.");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [checkNetwork, loadStoredPresence, savePresence]);

  // ==================== On‑Chain Anchoring ====================
  const anchorOnChain = useCallback(async () => {
    if (!presenceData || !wallet) {
      setError("No presence data to anchor.");
      return;
    }
    if (!window.ethereum) {
      setError("MetaMask not detected");
      return;
    }
    if (!CONTRACT_ADDRESS) {
      setError("Contract address not configured. Set VITE_RADIANT_CONTRACT_ADDRESS.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatusMessage("Preparing anchoring...");
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const isNetOk = await checkNetwork(provider);
      if (!isNetOk) {
        setLoading(false);
        return;
      }
      const signer = await provider.getSigner();
      const contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);
      setStatusMessage("Sending transaction...");
      const tx = await contract.registerPresence(
        presenceData.identifier,
        presenceData.score,
        presenceData.firstSeen
      );
      setStatusMessage("Waiting for confirmation...");
      await tx.wait();
      const updated = { ...presenceData, anchored: true };
      savePresence(updated);
      setStatusMessage("✅ Successfully anchored on‑chain!");
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Anchoring failed.");
      setStatusMessage(null);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [presenceData, wallet, checkNetwork, savePresence]);

  // ==================== Event Listeners ====================
  useEffect(() => {
    mountedRef.current = true;
    const stored = localStorage.getItem("radiant_presence");
    if (stored) {
      try {
        const data = JSON.parse(stored) as PresenceData;
        setPresenceData(data);
        setWallet(data.identifier);
      } catch {}
    }

    if (!window.ethereum) return;

    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        disconnect();
      } else {
        const newAddress = accounts[0];
        if (newAddress !== wallet) {
          const existing = loadStoredPresence(newAddress);
          if (existing) {
            setPresenceData(existing);
            setWallet(newAddress);
          } else {
            disconnect();
          }
        }
      }
    };

    const handleChainChanged = () => {
      window.location.reload();
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);

    return () => {
      mountedRef.current = false;
      window.ethereum?.removeListener("accountsChanged", handleAccountsChanged);
      window.ethereum?.removeListener("chainChanged", handleChainChanged);
    };
  }, [wallet, disconnect, loadStoredPresence]);

  // ==================== Render ====================
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

          {error && (
            <div className="p-3 bg-red-900/50 text-red-300 rounded-xl text-sm break-words">
              {error}
            </div>
          )}
          {statusMessage && (
            <div className="p-3 bg-blue-900/50 text-blue-300 rounded-xl text-sm">
              {statusMessage}
            </div>
          )}

          {!isCorrectNetwork && (
            <div className="p-3 bg-yellow-900/30 text-yellow-300 rounded-xl text-sm space-y-2">
              <p>⚠️ Wrong network. Please switch to {EXPECTED_CHAIN_NAME}.</p>
              <Button
                onClick={switchNetwork}
                disabled={isSwitchingNetwork}
                variant="secondary"
                size="sm"
                className="w-full"
              >
                {isSwitchingNetwork ? "Switching..." : `Switch to ${EXPECTED_CHAIN_NAME}`}
              </Button>
            </div>
          )}

          {!presenceData ? (
            <Button
              onClick={connectAndRegister}
              disabled={loading || !isCorrectNetwork}
              className="w-full"
            >
              {loading ? (
                <>
                  <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Connecting...
                </>
              ) : (
                "Connect Wallet & Register Presence"
              )}
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-zinc-800 text-left space-y-2">
                <p><strong>Identifier:</strong> {formatAddress(presenceData.identifier)}</p>
                <p><strong>Presence Score:</strong> {presenceData.score}/100</p>
                <p><strong>First seen:</strong> {formatDate(presenceData.firstSeen)}</p>
                <p><strong>Anchored on‑chain:</strong> {presenceData.anchored ? "✅ Yes" : "❌ No"}</p>
              </div>

              <div className="flex gap-2">
                {!presenceData.anchored && (
                  <Button
                    onClick={anchorOnChain}
                    disabled={loading || !isCorrectNetwork}
                    variant="outline"
                    className="flex-1"
                  >
                    {loading ? (
                      <>
                        <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                        Anchoring...
                      </>
                    ) : (
                      "Anchor on‑chain"
                    )}
                  </Button>
                )}
                <Button
                  onClick={disconnect}
                  variant="ghost"
                  className="flex-1"
                  disabled={loading}
                >
                  Disconnect
                </Button>
              </div>

              {/* Share Button & Dialog */}
              <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="secondary" className="w-full gap-2">
                    <Share2 className="w-4 h-4" />
                    Share Your Score
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-zinc-900 border-zinc-800 text-white">
                  <DialogHeader>
                    <DialogTitle>Share Your Radiant Presence</DialogTitle>
                    <DialogDescription className="text-zinc-400">
                      Let the world know you're part of the CIS Radiant Protocol.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="flex flex-col gap-3 py-4">
                    <Button
                      onClick={() => {
                        shareToX(presenceData.score, presenceData.anchored);
                        setShareDialogOpen(false);
                      }}
                      className="bg-black hover:bg-zinc-800 text-white border border-zinc-700 gap-2"
                    >
                      <X className="w-4 h-4" />
                      Share on X
                    </Button>
                    <Button
                      onClick={() => {
                        shareToFarcaster(presenceData.score, presenceData.anchored);
                        setShareDialogOpen(false);
                      }}
                      className="bg-purple-900 hover:bg-purple-800 text-white gap-2"
                    >
                      <MessageCircle className="w-4 h-4" />
                      Share on Farcaster
                    </Button>
                  </div>
                  <p className="text-xs text-zinc-500 text-center">
                    Your score and a link to Radiant Protocol will be shared.
                  </p>
                </DialogContent>
              </Dialog>

              {!CONTRACT_ADDRESS && !presenceData.anchored && (
                <p className="text-xs text-yellow-400">
                  ℹ️ Contract address not set. Anchoring is simulated (no on‑chain record).
                </p>
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
