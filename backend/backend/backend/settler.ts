import { Kafka } from 'kafkajs';
import { ethers } from 'ethers';
import * as dotenv from 'dotenv';

dotenv.config();

const kafka = new Kafka({ brokers: [process.env.KAFKA_BROKER!] });
const consumer = kafka.consumer({ groupId: 'settler-group' });

// The Law: Connecting to the Smart Contract on Arbitrum
const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
const contract = new ethers.Contract(process.env.CONTRACT_ADDRESS!, [
  "function participateGenesis(bytes32 hash) external"
], wallet);

const run = async () => {
  await consumer.connect();
  await consumer.subscribe({ topic: 'radiant-proofs', fromBeginning: true });

  await consumer.run({
    eachMessage: async ({ message }) => {
      const data = JSON.parse(message.value!.toString());
      console.log(`Settling proof for: ${data.address}`);

      try {
        // Triggering the blockchain payment - Presence becomes Value
        const tx = await contract.participateGenesis(data.hash);
        await tx.wait();
        console.log(`Success! Transaction: ${tx.hash}`);
      } catch (e) {
        console.error("Settlement Failed", e);
      }
    },
  });
};

run();

