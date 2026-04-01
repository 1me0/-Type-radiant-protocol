import { ethers } from "ethers";

/**
 * ARCHITECT CONFIGURATION
 * Replace these placeholders with your actual deployment data
 */
const CONTRACT_ADDRESS = "0xYourDeployedRadiantContractAddress";

// Minimal ABI for the functions we need to call
const RADIANT_ABI = [
    "function submitCISScore(uint256 score, bytes32 messageHash, bytes memory signature) external",
    "function users(address) view returns (uint256 reputation, uint256 rewards, bool exists)",
    "event CISScoreSubmitted(address indexed user, uint256 score, uint256 reward)"
];

/**
 * @dev Submits a calculated CIS score to the Radiant Protocol.
 * @param {number} score - The floating point score (e.g., 8.5)
 * @param {string} messageText - The original content that was scored
 */
export async function submitScoreToContract(score, messageText) {
    // 1. Connectivity Check
    if (!window.ethereum) {
        alert("MetaMask not detected. Please install the extension to claim rewards.");
        return;
    }

    try {
        // 2. Initialize Provider and Signer
        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        const userAddress = await signer.getAddress();
        
        console.log(`Architect identified: ${userAddress}`);

        // 3. Prepare and Scale Data (The 1% Leverage)
        // Normalizes 0.0-10.0 scale to 0-1000 for Solidity uint256
        const scaledScore = Math.min(Math.floor(score * 100), 1000);
        const message = `Radiant CIS Score: ${scaledScore} | Content: ${messageText}`;
        
        // 4. Cryptographic Proof (EIP-191)
        console.log("Requesting signature for integrity proof...");
        const signature = await signer.signMessage(message);
        const messageHash = ethers.hashMessage(message);

        // 5. Execute Contract Call
        const contract = new ethers.Contract(CONTRACT_ADDRESS, RADIANT_ABI, signer);
        
        console.log("Transmitting to Radiant Protocol...");
        const tx = await contract.submitCISScore(scaledScore, messageHash, signature);
        
        // 6. Await Manifestation
        const receipt = await tx.wait();
        console.log("Transaction confirmed:", receipt.hash);
        
        alert(`Success! Logic integrated. Reputation increased by ${scaledScore / 10}.`);
        return receipt;
        
    } catch (error) {
        console.error("Radiant Protocol Error:", error);
        
        // Handle common user errors
        if (error.code === "ACTION_REJECTED") {
            alert("Signature rejected. Transaction cancelled.");
        } else {
            alert("Execution failed. See console for technical details.");
        }
        throw error;
    }
}
