// RadiantSDK.ts
// TypeScript SDK for interacting with the Radiant Protocol smart contract.
// Includes gas estimation and cost preview for every transaction.

import { ethers, Contract, Signer, Provider, TransactionReceipt, EventLog, Log } from 'ethers';

// ============================================================
// ABI – Full interface including all functions and events
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
    // Reputation helper
    "function getReputation(address user) external view returns (uint256)",
    // Events
    "event Staked(address indexed user, uint256 amount)",
    "event ProofSubmitted(address indexed user, string proofHash)",
    "event Claimed(address indexed user, uint256 amount)",
    "event PointsConverted(address indexed user, uint256 points, uint256 radAmount)"
];

// ============================================================
// Custom Error Classes
// ============================================================
export class RadiantSDKError extends Error {
    constructor(message: string) {
        super(`[RadiantSDK] ${message}`);
        this.name = 'RadiantSDKError';
    }
}

export class RadiantNetworkError extends RadiantSDKError {
    constructor(expectedChainId: number, actualChainId: number) {
        super(`Network mismatch: expected chain ID ${expectedChainId}, got ${actualChainId}`);
        this.name = 'RadiantNetworkError';
    }
}

// ============================================================
// Type Definitions
// ============================================================
export interface UserStats {
    stake: string;        // formatted RAD (e.g., "10.5")
    reputation: number;    // integer reputation score
    rewards: string;       // formatted RAD pending
    stakeRaw: bigint;      // raw wei equivalent (18 decimals)
    rewardsRaw: bigint;    // raw wei equivalent
}

export interface StakedEvent {
    user: string;
    amount: bigint;
}

export interface ProofSubmittedEvent {
    user: string;
    proofHash: string;
}

export interface ClaimedEvent {
    user: string;
    amount: bigint;
}

export interface PointsConvertedEvent {
    user: string;
    points: bigint;
    radAmount: bigint;
}

export interface RadiantSDKOptions {
    /** Expected chain ID (optional, if provided will validate on each call) */
    chainId?: number;
    /** Number of confirmations to wait for transactions (default: 1) */
    confirmations?: number;
    /** Gas limit multiplier for safety (e.g., 1.2 = 20% buffer). Default: 1.1 */
    gasLimitMultiplier?: number;
    /** Callback invoked before sending a transaction with gas estimate */
    onBeforeTransaction?: (estimate: GasEstimate) => void;
}

export interface GasEstimate {
    /** Estimated gas units required */
    gasLimit: bigint;
    /** Current gas price (in wei) */
    gasPrice: bigint;
    /** Estimated cost in ETH (as string) */
    estimatedCostEth: string;
    /** Estimated cost in wei */
    estimatedCostWei: bigint;
}

// ============================================================
// Main SDK Class
// ============================================================
export class RadiantSDK {
    private contract: Contract;
    private signer: Signer;
    private provider: Provider;
    private options: Required<Omit<RadiantSDKOptions, 'onBeforeTransaction'>> & Pick<RadiantSDKOptions, 'onBeforeTransaction'>;
    public readonly TOKEN_DECIMALS = 18;

    /**
     * Creates a new RadiantSDK instance.
     * @param contractAddress – Deployed contract address.
     * @param signer – ethers Signer (e.g., from MetaMask or a private key wallet).
     * @param options – Optional configuration (chainId, confirmations, gasLimitMultiplier, onBeforeTransaction).
     */
    constructor(contractAddress: string, signer: Signer, options: RadiantSDKOptions = {}) {
        if (!ethers.isAddress(contractAddress)) {
            throw new RadiantSDKError('Invalid contract address');
        }
        this.signer = signer;
        this.provider = signer.provider!;
        if (!this.provider) {
            throw new RadiantSDKError('Signer must have a provider');
        }
        this.contract = new Contract(contractAddress, CONTRACT_ABI, signer);
        this.options = {
            chainId: options.chainId ?? 0,
            confirmations: options.confirmations ?? 1,
            gasLimitMultiplier: options.gasLimitMultiplier ?? 1.1,
            onBeforeTransaction: options.onBeforeTransaction,
        };
    }

    /**
     * Validates that the signer is connected to the expected network (if chainId provided).
     */
    private async validateNetwork(): Promise<void> {
        if (this.options.chainId > 0) {
            const network = await this.provider.getNetwork();
            if (Number(network.chainId) !== this.options.chainId) {
                throw new RadiantNetworkError(this.options.chainId, Number(network.chainId));
            }
        }
    }

    /**
     * Estimate gas for a transaction and return cost details.
     * @param tx – The contract method call (e.g., contract.stake({ value: ... }))
     * @returns GasEstimate object
     */
    private async estimateGas(tx: Promise<ethers.ContractTransactionResponse> | ethers.ContractTransaction): Promise<GasEstimate> {
        // For ethers v6, we can get the transaction request and estimate gas
        let gasLimit: bigint;
        try {
            // If tx is a promise, we need to get the underlying transaction request.
            // Since we can't easily extract the unsigned tx from the promise, we'll use the contract's estimateGas method directly.
            // We'll refactor executeTransaction to use a function that returns the populated transaction.
            // For now, we'll estimate via provider.estimateGas with a dummy transaction.
            // This is a bit hacky; better to pass the method and args separately.
            // We'll change executeTransaction to accept a function returning the populated tx.
            throw new Error('Use estimateGasForMethod instead');
        } catch {
            // Fallback: use generic estimate
            const feeData = await this.provider.getFeeData();
            const gasPrice = feeData.gasPrice ?? 0n;
            return {
                gasLimit: 0n,
                gasPrice,
                estimatedCostEth: '0',
                estimatedCostWei: 0n,
            };
        }
    }

    /**
     * Estimates gas for a specific contract method call.
     * @param method – Contract method name
     * @param args – Arguments for the method
     * @param overrides – Optional transaction overrides (value, from, etc.)
     */
    async estimateGasForMethod(
        method: string,
        args: any[],
        overrides: ethers.Overrides = {}
    ): Promise<GasEstimate> {
        await this.validateNetwork();
        const populated = await this.contract[method].populateTransaction(...args, overrides);
        const gasLimit = await this.provider.estimateGas(populated);
        const feeData = await this.provider.getFeeData();
        const gasPrice = feeData.gasPrice ?? 0n;
        const estimatedCostWei = gasLimit * gasPrice;
        const estimatedCostEth = ethers.formatEther(estimatedCostWei);
        return { gasLimit, gasPrice, estimatedCostEth, estimatedCostWei };
    }

    /**
     * Executes a contract call, handling gas estimation, logging, and confirmation.
     * @param method – Contract method name
     * @param args – Arguments for the method
     * @param overrides – Optional transaction overrides (value, from, etc.)
     * @param customGasLimit – If provided, overrides the estimated gas (with multiplier)
     */
    private async executeTransaction(
        method: string,
        args: any[],
        overrides: ethers.Overrides = {},
        customGasLimit?: bigint
    ): Promise<TransactionReceipt> {
        await this.validateNetwork();

        // Estimate gas first (unless custom gas limit provided)
        let gasLimit: bigint;
        let gasEstimate: GasEstimate | undefined;
        if (customGasLimit) {
            gasLimit = customGasLimit;
        } else {
            gasEstimate = await this.estimateGasForMethod(method, args, overrides);
            gasLimit = gasEstimate.gasLimit * BigInt(Math.floor(this.options.gasLimitMultiplier * 100)) / 100n;
            gasEstimate.gasLimit = gasLimit; // update to buffered limit
        }

        // Fetch current gas price
        const feeData = await this.provider.getFeeData();
        const gasPrice = feeData.gasPrice ?? 0n;
        const finalEstimate: GasEstimate = gasEstimate ?? {
            gasLimit,
            gasPrice,
            estimatedCostWei: gasLimit * gasPrice,
            estimatedCostEth: ethers.formatEther(gasLimit * gasPrice),
        };

        // Notify via callback or console
        console.log(
            `⛽ Estimated gas: ${finalEstimate.gasLimit.toString()} units @ ${ethers.formatUnits(finalEstimate.gasPrice, 'gwei')} gwei → cost: ${finalEstimate.estimatedCostEth} ETH`
        );
        if (this.options.onBeforeTransaction) {
            this.options.onBeforeTransaction(finalEstimate);
        }

        // Build transaction overrides with gas limit and gas price
        const txOverrides: ethers.Overrides = {
            ...overrides,
            gasLimit: finalEstimate.gasLimit,
            gasPrice: finalEstimate.gasPrice,
        };

        // Send transaction
        const tx = await this.contract[method](...args, txOverrides);
        console.log(`📤 Transaction sent: ${tx.hash}`);

        const receipt = await tx.wait(this.options.confirmations);
        if (!receipt || receipt.status === 0) {
            throw new RadiantSDKError(`Transaction failed: ${tx.hash}`);
        }
        console.log(`✅ Confirmed in block ${receipt.blockNumber}`);
        return receipt;
    }

    // ==================== Core Protocol Functions ====================

    /**
     * Convert CIS points (earned from the Truth Engine) into RAD tokens.
     * @param points – Number of points (positive integer).
     * @param customGasLimit – Optional custom gas limit (overrides estimation).
     * @returns Transaction receipt.
     */
    async convertPointsToRAD(points: number | bigint, customGasLimit?: bigint): Promise<TransactionReceipt> {
        const pointsBigInt = BigInt(points);
        if (pointsBigInt <= 0n) {
            throw new RadiantSDKError('Points must be a positive integer');
        }
        console.log(`🔄 Converting ${pointsBigInt.toString()} points to RAD...`);
        return this.executeTransaction('convertPointsToRAD', [pointsBigInt], {}, customGasLimit);
    }

    /**
     * Stake ETH to participate in the protocol.
     * @param amountEth – Amount in ETH as string (e.g., "0.01").
     * @param customGasLimit – Optional custom gas limit.
     * @returns Transaction receipt.
     */
    async stake(amountEth: string, customGasLimit?: bigint): Promise<TransactionReceipt> {
        const amountWei = ethers.parseEther(amountEth);
        console.log(`🔒 Staking ${amountEth} ETH...`);
        return this.executeTransaction('stake', [], { value: amountWei }, customGasLimit);
    }

    /**
     * Submit a proof hash (e.g., from a conversation or presence event).
     * @param proofHash – String hash or identifier.
     * @param customGasLimit – Optional custom gas limit.
     * @returns Transaction receipt.
     */
    async submitProof(proofHash: string, customGasLimit?: bigint): Promise<TransactionReceipt> {
        if (!proofHash || proofHash.trim() === '') {
            throw new RadiantSDKError('Proof hash cannot be empty');
        }
        console.log(`📝 Submitting proof: ${proofHash.slice(0, 10)}...`);
        return this.executeTransaction('submitProof', [proofHash], {}, customGasLimit);
    }

    /**
     * Claim accumulated rewards (ETH or tokens) from staking and proof verification.
     * @param customGasLimit – Optional custom gas limit.
     * @returns Transaction receipt.
     */
    async claim(customGasLimit?: bigint): Promise<TransactionReceipt> {
        console.log(`💰 Claiming rewards...`);
        return this.executeTransaction('claim', [], {}, customGasLimit);
    }

    // ==================== Read‑Only Functions ====================

    /**
     * Load user statistics (stake, reputation, rewards).
     * @param address – User's wallet address.
     * @returns UserStats object with formatted and raw values.
     */
    async loadUserStats(address: string): Promise<UserStats> {
        if (!ethers.isAddress(address)) {
            throw new RadiantSDKError('Invalid address');
        }
        try {
            const result = await this.contract.users(address);
            const stakeRaw: bigint = result[0];
            const reputation: bigint = result[1];
            const rewardsRaw: bigint = result[2];

            return {
                stake: ethers.formatUnits(stakeRaw, this.TOKEN_DECIMALS),
                reputation: Number(reputation),
                rewards: ethers.formatUnits(rewardsRaw, this.TOKEN_DECIMALS),
                stakeRaw,
                rewardsRaw,
            };
        } catch (error) {
            console.error('Failed to load user stats:', error);
            throw new RadiantSDKError(`Failed to load stats for ${address}: ${error}`);
        }
    }

    /**
     * Get the reputation score for a user.
     * @param address – User's wallet address.
     * @returns Reputation as a number.
     */
    async getReputation(address: string): Promise<number> {
        if (!ethers.isAddress(address)) {
            throw new RadiantSDKError('Invalid address');
        }
        const rep = await this.contract.getReputation(address);
        return Number(rep);
    }

    // ==================== Event Listeners ====================

    /**
     * Subscribe to Staked events.
     * @param callback – Function called with event data.
     * @returns Unsubscribe function.
     */
    onStaked(callback: (event: StakedEvent) => void): () => void {
        const listener = (user: string, amount: bigint, event: EventLog) => {
            callback({ user, amount });
        };
        this.contract.on('Staked', listener);
        return () => this.contract.off('Staked', listener);
    }

    /**
     * Subscribe to ProofSubmitted events.
     * @param callback – Function called with event data.
     * @returns Unsubscribe function.
     */
    onProofSubmitted(callback: (event: ProofSubmittedEvent) => void): () => void {
        const listener = (user: string, proofHash: string, event: EventLog) => {
            callback({ user, proofHash });
        };
        this.contract.on('ProofSubmitted', listener);
        return () => this.contract.off('ProofSubmitted', listener);
    }

    /**
     * Subscribe to Claimed events.
     * @param callback – Function called with event data.
     * @returns Unsubscribe function.
     */
    onClaimed(callback: (event: ClaimedEvent) => void): () => void {
        const listener = (user: string, amount: bigint, event: EventLog) => {
            callback({ user, amount });
        };
        this.contract.on('Claimed', listener);
        return () => this.contract.off('Claimed', listener);
    }

    /**
     * Subscribe to PointsConverted events.
     * @param callback – Function called with event data.
     * @returns Unsubscribe function.
     */
    onPointsConverted(callback: (event: PointsConvertedEvent) => void): () => void {
        const listener = (user: string, points: bigint, radAmount: bigint, event: EventLog) => {
            callback({ user, points, radAmount });
        };
        this.contract.on('PointsConverted', listener);
        return () => this.contract.off('PointsConverted', listener);
    }

    // ==================== Utility Methods ====================

    /**
     * Get the contract address.
     */
    getContractAddress(): string {
        return this.contract.target as string;
    }

    /**
     * Get the signer's wallet address.
     */
    async getSignerAddress(): Promise<string> {
        return await this.signer.getAddress();
    }

    /**
     * Get the underlying ethers.Contract instance (for advanced usage).
     */
    getContract(): Contract {
        return this.contract;
    }

    /**
     * Get the current chain ID.
     */
    async getChainId(): Promise<number> {
        return Number((await this.provider.getNetwork()).chainId);
    }

    /**
     * Format RAD token amount from wei (18 decimals) to a decimal string.
     */
    formatRAD(wei: bigint): string {
        return ethers.formatUnits(wei, this.TOKEN_DECIMALS);
    }

    /**
     * Parse RAD token amount to wei.
     */
    parseRAD(rad: string): bigint {
        return ethers.parseUnits(rad, this.TOKEN_DECIMALS);
    }

    /**
     * Get current gas price from the provider.
     */
    async getGasPrice(): Promise<bigint> {
        const feeData = await this.provider.getFeeData();
        return feeData.gasPrice ?? 0n;
    }
}

// ============================================================
// Example usage (commented out)
// ============================================================
/*
async function example() {
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const sdk = new RadiantSDK('0xYourContractAddress', signer, {
        chainId: 1,
        confirmations: 1,
        gasLimitMultiplier: 1.2,
        onBeforeTransaction: (estimate) => {
            console.log(`Transaction will cost ~${estimate.estimatedCostEth} ETH`);
        }
    });

    // Stake 0.01 ETH (gas will be estimated and logged)
    await sdk.stake('0.01');

    // Or get a gas estimate without sending:
    const estimate = await sdk.estimateGasForMethod('stake', [], { value: ethers.parseEther('0.01') });
    console.log(`Staking will cost ~${estimate.estimatedCostEth} ETH`);
}
*/
