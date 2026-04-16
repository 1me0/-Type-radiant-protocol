import { Kafka } from 'kafkajs';
import { ethers } from 'ethers';
import * as dotenv from 'dotenv';

dotenv.config();

// ============================================================
// Environment validation
// ============================================================
const requiredEnv = [
    'KAFKA_BROKER',
    'RPC_URL',
    'PRIVATE_KEY',
    'CONTRACT_ADDRESS'
];

for (const env of requiredEnv) {
    if (!process.env[env]) {
        console.error(`Missing required environment variable: ${env}`);
        process.exit(1);
    }
}

const KAFKA_BROKER = process.env.KAFKA_BROKER!;
const RPC_URL = process.env.RPC_URL!;
const PRIVATE_KEY = process.env.PRIVATE_KEY!;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS!;
const TOPIC = process.env.KAFKA_TOPIC || 'radiant-proofs';
const GROUP_ID = process.env.KAFKA_GROUP_ID || 'settler-group';

// ============================================================
// Kafka setup
// ============================================================
const kafka = new Kafka({ brokers: [KAFKA_BROKER] });
const consumer = kafka.consumer({ groupId: GROUP_ID });

// ============================================================
// Ethereum setup
// ============================================================
const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
const contract = new ethers.Contract(
    CONTRACT_ADDRESS,
    [
        "function participateGenesis(bytes32 hash) external",
        "event GenesisParticipation(address indexed user, bytes32 hash, uint256 timestamp)"
    ],
    wallet
);

// ============================================================
// Graceful shutdown
// ============================================================
const shutdown = async () => {
    console.log('Shutting down settler...');
    await consumer.disconnect();
    process.exit(0);
};

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// ============================================================
// Main consumer loop
// ============================================================
const run = async () => {
    console.log(`Connecting to Kafka broker: ${KAFKA_BROKER}`);
    await consumer.connect();
    await consumer.subscribe({ topic: TOPIC, fromBeginning: true });
    console.log(`Subscribed to topic: ${TOPIC}`);

    await consumer.run({
        eachMessage: async ({ topic, partition, message }) => {
            const value = message.value?.toString();
            if (!value) {
                console.warn('Empty message received, skipping');
                return;
            }

            let data: { address?: string; hash?: string };
            try {
                data = JSON.parse(value);
            } catch (err) {
                console.error('Failed to parse message JSON:', err);
                return;
            }

            const { address, hash } = data;
            if (!address || !hash) {
                console.warn('Invalid message format (missing address or hash)', data);
                return;
            }

            console.log(`Settling proof for ${address} with hash ${hash.slice(0,10)}...`);

            try {
                const tx = await contract.participateGenesis(hash);
                console.log(`Transaction sent: ${tx.hash}`);
                const receipt = await tx.wait();
                console.log(`✅ Settlement confirmed in block ${receipt?.blockNumber}. Tx: ${tx.hash}`);
            } catch (err: any) {
                console.error(`❌ Settlement failed for ${address}:`, err.message || err);
            }
        },
    });
};

run().catch((err) => {
    console.error('Fatal error in settler:', err);
    process.exit(1);
});
