// worker/src/main.rs
// Nova folding worker for the Radiant Protocol.
// Receives proof packages from Kafka, pairs them by index, folds them, and forwards to the next level.

use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::message::Message;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::env;
use std::sync::Arc;
use tokio::sync::Mutex;
use std::time::Duration;
use tracing::{info, warn, error};
use tracing_subscriber;
use anyhow::Result;

// ----------------------------------------------------------------------
// Proof package (serialized over Kafka)
// ----------------------------------------------------------------------
#[derive(Serialize, Deserialize, Debug, Clone)]
struct ProofPackage {
    level: u32,
    index: u32,
    is_base: bool,
    data: Vec<u8>, // In production: serialized Nova proof
}

// ----------------------------------------------------------------------
// Worker state: buffer for pending proofs (thread‑safe)
// ----------------------------------------------------------------------
struct WorkerState {
    pending: HashMap<u32, ProofPackage>,
    folded_count: usize,
}

impl WorkerState {
    fn new() -> Self {
        Self {
            pending: HashMap::new(),
            folded_count: 0,
        }
    }

    /// Process an incoming proof. Returns a pair if a matching index is found.
    fn process(&mut self, incoming: ProofPackage) -> Option<(ProofPackage, ProofPackage)> {
        let pair_id = incoming.index / 2;
        if let Some(companion) = self.pending.remove(&pair_id) {
            Some((companion, incoming))
        } else {
            self.pending.insert(pair_id, incoming);
            None
        }
    }

    fn pending_count(&self) -> usize {
        self.pending.len()
    }

    fn folded_count(&self) -> usize {
        self.folded_count
    }
}

// ----------------------------------------------------------------------
// WebSocket heartbeat (simulated via HTTP POST)
// ----------------------------------------------------------------------
async fn send_ws_event(level: u32, pending: usize, folded: usize) {
    let ws_url = env::var("WS_URL").unwrap_or_else(|_| "http://localhost:8080".to_string());
    let client = reqwest::Client::new();
    let _ = client
        .post(&format!("{}/update", ws_url))
        .json(&serde_json::json!({
            "level": level,
            "pending": pending,
            "folded": folded
        }))
        .send()
        .await;
}

// ----------------------------------------------------------------------
// Main worker loop
// ----------------------------------------------------------------------
#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    let consume_topic = env::var("CONSUME_TOPIC").unwrap_or_else(|_| "level_0".to_string());
    let produce_topic = env::var("PRODUCE_TOPIC").unwrap_or_else(|_| "level_1".to_string());
    let level: u32 = env::var("LEVEL").unwrap_or_else(|_| "0".to_string()).parse()?;

    // Kafka consumer
    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", "kafka:9092")
        .set("group.id", &format!("worker-{}", level))
        .set("auto.offset.reset", "earliest")
        .create()?;
    consumer.subscribe(&[&consume_topic])?;

    // Kafka producer
    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", "kafka:9092")
        .create()?;

    // Shared state
    let state = Arc::new(Mutex::new(WorkerState::new()));
    let state_clone = state.clone();

    info!(
        "Worker level {} listening on '{}' -> producing to '{}'",
        level, consume_topic, produce_topic
    );

    // Heartbeat task (sends stats every 5 seconds)
    let heartbeat_handle = tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(5)).await;
            let (pending, folded) = {
                let guard = state_clone.lock().await;
                (guard.pending_count(), guard.folded_count())
            };
            send_ws_event(level, pending, folded).await;
        }
    });

    // Main processing loop
    let mut message_stream = consumer.stream();
    while let Some(msg) = message_stream.recv().await {
        match msg {
            Err(e) => error!("Kafka error: {}", e),
            Ok(msg) => {
                if let Some(payload) = msg.payload() {
                    match bincode::deserialize::<ProofPackage>(payload) {
                        Ok(incoming) => {
                            info!("Received proof index {} at level {}", incoming.index, level);
                            let mut guard = state.lock().await;
                            if let Some((p1, p2)) = guard.process(incoming) {
                                // --- Folding step (placeholder for real Nova proof folding) ---
                                // In production, you would:
                                // 1. Deserialize Nova proofs from p1.data and p2.data.
                                // 2. Use Nova's `fold` function to combine them.
                                // 3. Serialize the resulting proof into new.data.
                                let folded_proof = ProofPackage {
                                    level: level + 1,
                                    index: p1.index / 2,
                                    is_base: false,
                                    data: vec![], // placeholder
                                };
                                let serialized = bincode::serialize(&folded_proof)?;
                                let record = FutureRecord::to(&produce_topic)
                                    .payload(&serialized)
                                    .key(&folded_proof.index.to_string());
                                producer.send(record, Duration::from_secs(0)).await?;
                                guard.folded_count += 1;
                                info!("Folded and produced proof to level {}", level + 1);
                            }
                        }
                        Err(e) => error!("Deserialization error: {}", e),
                    }
                }
            }
        }
    }

    heartbeat_handle.abort();
    Ok(())
}
