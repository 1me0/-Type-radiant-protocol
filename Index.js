// index.js – Radiant Relayer Service
// Listens for ProofSubmitted events from the smart contract, forwards them to Kafka,
// and manages graceful shutdown.

const { ethers } = require("ethers");
const { Kafka } = require("kafkajs");
require("dotenv").config(); // Load environment variables from .env

// ============================================================
// Configuration
// ============================================================
const RPC_URL = process.env.RPC_URL || "http://ganache:8545";
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
const RELAYER_PRIVATE_KEY = process.env.RELAYER_PRIVATE_KEY;
const KAFKA_BROKER = process.env.KAFKA_BROKER || "kafka:9092";
const KAFKA_TOPIC = process.env.KAFKA_TOPIC || "proofs-raw";

// Validate required environment variables
if (!CONTRACT_ADDRESS) {
    console.error("FATAL: CONTRACT_ADDRESS not set in environment");
    process.exit(1);
}
if (!RELAYER_PRIVATE_KEY) {
    console.error("FATAL: RELAYER_PRIVATE_KEY not set in environment");
    process.exit(1);
}

// ABI – you must replace this with the actual ABI of your Radiant contract.
// For demonstration, we include only the event we need. Replace with full ABI.
const ABI = [
    "event ProofSubmitted(address indexed user, bytes32 proofHash)"
];

// ============================================================
// Initialize clients
// ============================================================
const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(RELAYER_PRIVATE_KEY, provider);
const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, wallet);
const kafka = new Kafka({ brokers: [KAFKA_BROKER] });
const producer = kafka.producer();

// ============================================================
// Graceful shutdown handling
// ============================================================
let isShuttingDown = false;

async function shutdown(signal) {
    if (isShuttingDown) return;
    isShuttingDown = true;
    console.log(`\n${signal} received, shutting down gracefully...`);
    try {
        // Stop listening to contract events
        contract.removeAllListeners();
        // Disconnect Kafka producer
        await producer.disconnect();
        console.log("Kafka producer disconnected");
    } catch (err) {
        console.error("Error during shutdown:", err);
    }
    process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

// ============================================================
// Main function
// ============================================================
async function start() {
    try {
        await producer.connect();
        console.log("Kafka producer connected");
        console.log(`Listening for ProofSubmitted events on contract ${CONTRACT_ADDRESS}...`);
    } catch (err) {
        console.error("Failed to connect Kafka producer:", err);
        process.exit(1);
    }

    contract.on("ProofSubmitted", async (user, proofHash, event) => {
        console.log(`Proof submitted by ${user}, hash: ${proofHash}`);
        try {
            await producer.send({
                topic: KAFKA_TOPIC,
                messages: [{
                    value: JSON.stringify({
                        user,
                        proofHash,
                        blockNumber: event.log.blockNumber,
                        transactionHash: event.log.transactionHash,
                        timestamp: Date.now()
                    })
                }]
            });
            console.log(`Proof forwarded to Kafka topic "${KAFKA_TOPIC}"`);
        } catch (err) {
            console.error("Failed to send message to Kafka:", err);
            // Optionally implement retry logic here
        }
    });

    // Also listen for provider errors (e.g., connection lost)
    provider.on("error", (err) => {
        console.error("Provider error:", err);
        shutdown("PROVIDER_ERROR");
    });
}

// Start the relayer
start().catch((err) => {
    console.error("Fatal error starting relayer:", err);
    process.exit(1);
});
