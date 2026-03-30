FROM rust:1.70 as builder
WORKDIR /usr/src/worker
COPY Cargo.toml .
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
COPY src/ src/
RUN cargo build --release

FROM debian:bullseye-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/src/worker/target/release/radiant-worker /usr/local/bin/radiant-worker
CMD ["radiant-worker"]
