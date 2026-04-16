import { ethers } from 'ethers';

// ============================================================
// ABI – Replace with your actual contract ABI after compilation
// ============================================================
const CONTRACT_ABI = [
    // Token conversion
    "function convertPointsToRAD(uint256 points) external",
    // Staking
    "function stake() external payable",
    // Proof submission
    "function submitProof(string memory proofHash) external",
    // Reward claim
    "function claim() external",
    // User data
    "function users(address) view returns (uint256 stake, uint256 reputation, uint256 rewards)",
    // Additional helper (optional)
    "function getReputation(address user) external view returns (uint256)",
    // Events (optional, for listening)
    "event Staked(address indexed user, uint256 amount)",
    "event ProofSubmitted(address indexed user, string proofHash)",
    "event Claimed(address indexed user, uint256 amount)",
    "event PointsConverted(address indexed user, uint256 points, uint256 radAmount)"
];

// ============================================================
// SDK Class
// ============================================================
export class RadiantSDK {
    private contract: ethers.Contract;
    private signer: ethers.Signer;
    private provider: ethers.Provider;

    /**
     * Creates a new RadiantSDK instance.
     * @param contractAddress – deployed contract address
     * @param signer – ethers Signer (from MetaMask or other wallet)
     */
    constructor(contractAddress: string, signer: ethers.Signer) {
        this.signer = signer;
        this.provider = signer.provider!;
        this.contract = new ethers.Contract(contractAddress, CONTRACT_ABI, signer);
    }

    /**
     * Convert CIS points (earned from the Truth Engine) into $RAD tokens.
     * @param points – number of points (must be positive integer)
     */
    async convertPointsToRAD(points: number): Promise<ethers.TransactionReceipt> {
        if (!Number.isInteger(points) || points <= 0) {
            throw new Error('Points must be a positive integer');
        }
        console.log(`🔄 Converting ${points} points to RAD...`);
        const tx = await this.contract.convertPointsToRAD(points);
        const receipt = await tx.wait();
        console.log(`✅ Converted ${points} points → Tx: ${receipt?.hash}`);
        return receipt;
    }

    /**
     * Stake ETH to participate in the protocol.
     * @param amountEth – amount in ETH (e.g., "0.01")
     */
    async stake(amountEth: string): Promise<ethers.TransactionReceipt> {
        const amountWei = ethers.parseEther(amountEth);
        console.log(`🔒 Staking ${amountEth} ETH...`);
        const tx = await this.contract.stake({ value: amountWei });
        const receipt = await tx.wait();
        console.log(`✅ Staked ${amountEth} ETH → Tx: ${receipt?.hash}`);
        return receipt;
    }

    /**
     * Submit a proof hash (e.g., from a conversation or presence event).
     * @param proofHash – string hash (can be any identifier)
     */
    async submitProof(proofHash: string): Promise<ethers.TransactionReceipt> {
        if (!proofHash || proofHash.trim() === '') {
            throw new Error('Proof hash cannot be empty');
        }
        console.log(`📝 Submitting proof: ${proofHash.slice(0, 10)}...`);
        const tx = await this.contract.submitProof(proofHash);
        const receipt = await tx.wait();
        console.log(`✅ Proof submitted → Tx: ${receipt?.hash}`);
        return receipt;
    }

    /**
     * Claim accumulated rewards (ETH or tokens) from staking and proof verification.
     */
    async claim(): Promise<ethers.TransactionReceipt> {
        console.log(`💰 Claiming rewards...`);
        const tx = await this.contract.claim();
        const receipt = await tx.wait();
        console.log(`✅ Rewards claimed → Tx: ${receipt?.hash}`);
        return receipt;
    }

    /**
     * Load user statistics (stake, reputation, rewards).
     * @param address – user's wallet address
     */
    async loadUserStats(address: string): Promise<{
        stake: string;
        reputation: number;
        rewards: string;
    }> {
        try {
            const user = await this.contract.users(address);
            return {
                stake: ethers.formatEther(user.stake),
                reputation: Number(user.reputation),
                rewards: ethers.formatEther(user.rewards)
            };
        } catch (error) {
            console.error('Failed to load user stats:', error);
            return { stake: '0', reputation: 0, rewards: '0' };
        }
    }

    /**
     * Get the contract address.
     */
    getContractAddress(): string {
        return this.contract.target as string;
    }

    /**
     * Get the signer's address.
     */
    async getSignerAddress(): Promise<string> {
        return await this.signer.getAddress();
    }
}

// ============================================================
// Example usage (commented out)
// ============================================================
/*
async function example() {
    // In a browser environment with MetaMask:
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const sdk = new RadiantSDK('0xYourContractAddress', signer);

    // Stake 0.01 ETH
    await sdk.stake('0.01');

    // Submit a proof
    await sdk.submitProof('0x123...');

    // Claim rewards
    await sdk.claim();

    // Get user stats
    const stats = await sdk.loadUserStats(await sdk.getSignerAddress());
    console.log(stats);
}
*/
