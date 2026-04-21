// frontend/contractInterop.ts
// Radiant Protocol – Contract Interaction for CIS Score Submission

import { ethers } from 'ethers';

// ABI for the Radiant contract (minimal – adjust according to your contract)
const RADIANT_ABI = [
  "function submitCISScore(uint256 score, bytes32 messageHash, bytes memory signature) external",
  "event CISScoreSubmitted(address indexed user, uint256 score, uint256 reward)",
];

// Contract address – should be set via environment variable
const CONTRACT_ADDRESS = process.env.REACT_APP_CONTRACT_ADDRESS || '0x...';

// Expected chain ID (Sepolia by default)
const EXPECTED_CHAIN_ID = 11155111;
const EXPECTED_CHAIN_NAME = 'Sepolia';

/**
 * Submits a CIS score to the Radiant Protocol smart contract.
 * The score is signed together with the message text to prove authenticity.
 *
 * @param score - CIS score (0‑10, floating point)
 * @param messageText - The original message or context that was scored
 * @returns Promise<ethers.TransactionReceipt>
 * @throws Error if wallet not connected, wrong network, or transaction fails
 */
export async function submitScoreToContract(
  score: number,
  messageText: string
): Promise<ethers.TransactionReceipt> {
  // 1. Validate inputs
  if (typeof score !== 'number' || isNaN(score) || score < 0 || score > 10) {
    throw new Error('Invalid CIS score: must be a number between 0 and 10.');
  }
  if (!messageText || typeof messageText !== 'string') {
    throw new Error('Message text is required.');
  }

  // 2. Check MetaMask availability
  if (!window.ethereum) {
    throw new Error('MetaMask not detected. Please install MetaMask to claim rewards.');
  }

  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();

  // 3. Validate network
  const network = await provider.getNetwork();
  const chainId = Number(network.chainId);
  if (chainId !== EXPECTED_CHAIN_ID) {
    throw new Error(`Please switch to ${EXPECTED_CHAIN_NAME} (chain ID ${EXPECTED_CHAIN_ID}). Current: ${chainId}`);
  }

  // 4. Prepare data
  const scaledScore = Math.min(Math.floor(score * 100), 1000); // 0‑10 → 0‑1000
  const message = `Radiant CIS Score: ${scaledScore} | Content: ${messageText}`;

  // 5. Sign message (EIP‑191)
  const signature = await signer.signMessage(message);
  const messageHash = ethers.hashMessage(message);

  // 6. Instantiate contract
  const contract = new ethers.Contract(CONTRACT_ADDRESS, RADIANT_ABI, signer);

  // 7. Send transaction
  console.log(`Submitting CIS score ${score} (scaled ${scaledScore}) to Radiant Protocol...`);
  const tx = await contract.submitCISScore(scaledScore, messageHash, signature);

  // 8. Wait for confirmation
  const receipt = await tx.wait();
  console.log(`Transaction confirmed: ${receipt?.hash}`);

  // Optionally parse the event to get reward amount
  const iface = new ethers.Interface(RADIANT_ABI);
  let reward = null;
  for (const log of receipt?.logs || []) {
    try {
      const parsed = iface.parseLog(log);
      if (parsed && parsed.name === 'CISScoreSubmitted') {
        reward = parsed.args.reward.toString();
        break;
      }
    } catch (e) {
      // Not our event – continue
    }
  }
  if (reward) {
    console.log(`Reward earned: ${reward} wei (or tokens)`);
  }

  alert(`Success! Reputation increased by ${scaledScore / 10}.`);
  return receipt!;
}
