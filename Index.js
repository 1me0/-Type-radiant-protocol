const { ethers } = require("ethers");
const { Kafka } = require("kafkajs");

const RPC_URL = process.env.RPC_URL || "http://ganache:8545";
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
const RELAYER_PRIVATE_KEY = process.env.RELAYER_PRIVATE_KEY;
const ABI = require("../contracts/Radiant.sol?abi"); // adjust path

const kafka = new Kafka({ brokers: ["kafka:9092"] });
const producer = kafka.producer();

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(RELAYER_PRIVATE_KEY, provider);
const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, wallet);

async function start() {
    await producer.connect();
    console.log("Relayer started, listening for ProofSubmitted...");

    contract.on("ProofSubmitted", async (user, proofHash, event) => {
        console.log(`Proof submitted by ${user}`);
        await producer.send({
            topic: "proofs-raw",
            messages: [{ value: JSON.stringify({ user, proofHash }) }]
        });
    });
}

start().catch(console.error);
