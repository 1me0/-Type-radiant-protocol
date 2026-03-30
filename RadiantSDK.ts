import { ethers } from 'ethers';
import { Contract, Signer } from 'ethers';

const CONTRACT_ABI = [ /* paste the full ABI from your contract compilation */ ];

export class RadiantSDK {
    private contract: Contract;
    private signer: Signer;

    constructor(contractAddress: string, signer: Signer) {
        this.signer = signer;
        this.contract = new ethers.Contract(contractAddress, CONTRACT_ABI, signer);
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
