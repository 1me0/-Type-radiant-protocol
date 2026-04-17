/**
 * contractInterop.js
 *
 * Radiant Protocol – Frontend Contract Interaction Module
 * Submits CIS scores to the blockchain with cryptographic proof (EIP‑191 signature).
 *
 * Author: Radiant Protocol
 * License: MIT
 */

import { ethers } from "ethers";

// ============================================================
// CONFIGURATION – Replace with your deployed contract address
// ============================================================
const CONTRACT_ADDRESS = "0xYourDeployedRadiantContractAddress";

// Minimal ABI for the functions we need to call (expand as needed)
const RADIANT_ABI = [
    "function submitCISScore(uint256 score, bytes32 messageHash, bytes memory signature) external",
    "function users(address) view returns (uint256 reputation, uint256 rewards, bool exists)",
    "event CISScoreSubmitted(address indexed user, uint256 score, uint256 reward)"
];

// Expected chain ID (e.g., 11155111 for Sepolia, 1 for mainnet)
const EXPECTED_CHAIN_ID = 11155111; // Sepolia testnet – adjust for your network
const EXPECTED_CHAIN_NAME = "Sepolia";

// ============================================================
// Helper: Check if MetaMask is installed and on the correct network
// ============================================================
async function checkWalletAndNetwork() {
    if (!window.ethereum) {
        throw new Error("MetaMask not detected. Please install the extension to claim rewards.");
    }

    const provider = new ethers.BrowserProvider(window.ethereum);
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);

    if (chainId !== EXPECTED_CHAIN_ID) {
        throw new Error(`Please switch to ${EXPECTED_CHAIN_NAME} (chain ID ${EXPECTED_CHAIN_ID}). Current chain: ${chainId}`);
    }

    return provider;
}

// ============================================================
// Main function: Submit a CIS score to the smart contract
// ============================================================
/**
 * Submits a calculated CIS score to the Radiant Protocol smart contract.
 *
 * @param {number} score - The CIS score (0‑10, floating point).
 * @param {string} messageText - The original content that was scored (e.g., user query or response).
 * @returns {Promise<ethers.TransactionReceipt>} Transaction receipt.
 */
export async function submitScoreToContract(score, messageText) {
    // Validate inputs
    if (typeof score !== "number" || isNaN(score) || score < 0 || score > 10) {
        throw new Error("Invalid CIS score: must be a number between 0 and 10.");
    }
    if (!messageText || typeof messageText !== "string") {
        throw new Error("Invalid messageText: must be a non‑empty string.");
    }

    let provider, signer, userAddress;

    try {
        // 1. Connectivity & network check
        provider = await checkWalletAndNetwork();
        signer = await provider.getSigner();
        userAddress = await signer.getAddress();
        console.log(`Architect identified: ${userAddress}`);

        // 2. Prepare data (scaling and message)
        // Scale 0‑10 → 0‑1000 for Solidity uint256 (0.01 precision)
        const scaledScore = Math.min(Math.floor(score * 100), 1000);
        const message = `Radiant CIS Score: ${scaledScore} | Content: ${messageText}`;

        // 3. Generate cryptographic proof (EIP‑191 signed message)
        console.log("Requesting signature for integrity proof...");
        const signature = await signer.signMessage(message);
        const messageHash = ethers.hashMessage(message);

        // 4. Execute contract call
        const contract = new ethers.Contract(CONTRACT_ADDRESS, RADIANT_ABI, signer);
        console.log("Transmitting to Radiant Protocol...");
        const tx = await contract.submitCISScore(scaledScore, messageHash, signature);

        // 5. Wait for confirmation
        const receipt = await tx.wait();
        console.log("Transaction confirmed:", receipt.hash);

        // Optional: parse event to get reward amount
        const iface = new ethers.Interface(RADIANT_ABI);
        let reward = null;
        for (const log of receipt.logs) {
            try {
                const parsed = iface.parseLog(log);
                if (parsed && parsed.name === "CISScoreSubmitted") {
                    reward = parsed.args.reward.toString();
                    console.log(`Reward earned: ${reward} wei (or tokens)`);
                    break;
                }
            } catch (e) {
                // Not our event – skip
            }
        }

        alert(`Success! CIS score submitted. Reputation increased by approximately ${(scaledScore / 10).toFixed(1)}.`);
        return receipt;
    } catch (error) {
        console.error("Radiant Protocol Error:", error);

        // User‑friendly error messages
        if (error.message.includes("User rejected")) {
            alert("Signature rejected. Transaction cancelled.");
        } else if (error.message.includes("Please switch to")) {
            alert(error.message);
        } else if (error.message.includes("MetaMask not detected")) {
            alert(error.message);
        } else {
            alert("Transaction failed. See console for details.");
        }
        throw error;
    }
}

// ============================================================
// Optional: Fetch user reputation and rewards from the contract
// ============================================================
export async function getUserStats(userAddress) {
    try {
        const provider = await checkWalletAndNetwork();
        const signer = await provider.getSigner();
        const contract = new ethers.Contract(CONTRACT_ADDRESS, RADIANT_ABI, signer);
        const [reputation, rewards, exists] = await contract.users(userAddress);
        return { reputation: reputation.toString(), rewards: rewards.toString(), exists };
    } catch (error) {
        console.error("Failed to fetch user stats:", error);
        return null;
    }
            }
