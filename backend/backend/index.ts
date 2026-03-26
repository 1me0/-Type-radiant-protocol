import express from 'express';
import { Kafka } from 'kafkajs';
import { WebSocketServer } from 'ws';
import * as dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(express.json());

const kafka = new Kafka({
  clientId: 'radiant-bridge',
  brokers: [process.env.KAFKA_BROKER || 'localhost:9092']
});

const producer = kafka.producer();
const wss = new WebSocketServer({ port: 8080 });

// The "Radiance Listener" - Receives proofs from the field
app.post('/submit-proof', async (req, res) => {
  const { address, hash, nonce } = req.body;
  
  await producer.connect();
  await producer.send({
    topic: 'radiant-proofs',
    messages: [{ value: JSON.stringify({ address, hash, nonce, timestamp: Date.now() }) }],
  });

  // Pulse the data to all active Dashboards
  wss.clients.forEach((client) => {
    if (client.readyState === 1) {
      client.send(JSON.stringify({ type: 'NEW_PROOF', address, hash }));
    }
  });

  res.status(200).send({ status: 'PROCESSED', message: 'Presence Recorded' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Radiant Bridge active on port ${PORT}`);
});
         
