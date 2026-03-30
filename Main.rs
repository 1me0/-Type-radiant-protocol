use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::message::Message;
use serde::{Serialize, Deserialize};
use tokio::time::Duration;

#[derive(Serialize, Deserialize, Debug)]
struct ProofMessage {
    user: String,
    proof_hash: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct ValidatedMessage {
    user: String,
    valid: bool,
    reward: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", "kafka:9092")
        .set("group.id", "worker-group")
        .create()?;
    consumer.subscribe(&["proofs-raw"])?;

    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", "kafka:9092")
        .create()?;

    println!("Worker started, listening for proofs...");

    loop {
        match consumer.recv().await {
            Err(e) => eprintln!("Kafka error: {}", e),
            Ok(msg) => {
                if let Some(payload) = msg.payload() {
                    if let Ok(proof) = serde_json::from_slice::<ProofMessage>(payload) {
                        println!("Validating proof from {}", proof.user);
                        // Simulate work (2 seconds)
                        tokio::time::sleep(Duration::from_secs(2)).await;

                        // Always valid for demo
                        let validated = ValidatedMessage {
                            user: proof.user,
                            valid: true,
                            reward: "0.001".to_string(),
                        };

                        let record = FutureRecord::to("proofs-validated")
                            .payload(&serde_json::to_vec(&validated)?)
                            .key(&validated.user);
                        producer.send(record, Duration::from_secs(0)).await?;

                        println!("Validated proof for {}", proof.user);
                    }
                }
            }
        }
    }
}
