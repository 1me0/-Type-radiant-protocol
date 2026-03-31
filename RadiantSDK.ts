import { ethers } from 'ethers';
import { Contract, Signer } from 'ethers';

// NOTE: You must paste your actual ABI here after running 'npx hardhat compile'
const CONTRACT_ABI = [
    "function convertPointsToRAD(uint256 points) external",
    "function stake() external payable",
    "function submitProof(string proofHash) external",
    "function claim() external",
    "function users(address) view returns (uint256 stake, uint256 reputation, uint256 rewards)"
];

export class RadiantSDK {
    private contract: Contract;
    private signer: Signer;

    constructor(contractAddress: string, signer: Signer) {
        this.signer = signer;
        this.contract = new ethers.Contract(contractAddress, CONTRACT_ABI, signer);
    }

    /**
     * @dev Bridges the HTML/Frontend points to the Sovereign $RAD Tokens
     * Matches the logic in Radiant (1).sol
     */
    async claimTokensToWallet(points: number) {
        try {
            console.log(`Initiating anchor for ${points} points...`);
            // This calls the conversion law in your smart contract
            const tx = await this.contract.convertPointsToRAD(points); 
            
            await tx.wait(); // Wait for the blockchain to confirm the "Energy"
            alert("Sovereign Energy Anchored to Wallet! $RAD minted.");
        } catch (error) {
            console.error("Anchoring failed:", error);
            alert("Failed to anchor points. Ensure you have 1000+ points and gas fee.");
        }
    }

    async stake(amountEth: string) {
        const tx = await this.contract.stake({ value: ethers.parseEther(amountEth) });
        await tx.wait();
    }

    async submitProof(proofHash: string) {
        const tx = await this.contract.submitProof(proofHash);
        await tx.wait();
    }

    async claim() {
        const tx = await this.contract.claim();
        await tx.wait();
    }

    async loadUserStats(address: string) {
        const user = await this.contract.users(address);
        return {
            stake: ethers.formatEther(user.stake),
            reputation: Number(user.reputation),
            rewards: ethers.formatEther(user.rewards)
        };
    }
}
