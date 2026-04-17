/**
 * frictionless.ts
 *
 * High‑throughput, fault‑tolerant task processor with circuit breaker, retries with exponential backoff,
 * dead‑letter queue, and concurrency control. Designed for the Radiant Protocol’s proof validation,
 * relay processing, and other critical asynchronous operations.
 *
 * Author: Radiant Protocol
 * License: MIT
 */

import { EventEmitter } from 'events';

// ------------------------------------------------------------
// Task Definition
// ------------------------------------------------------------
export interface Task<T = any> {
    /** Unique identifier for the task. */
    id: string;
    /** Async function that performs the work. */
    execute: () => Promise<T>;
    /** Current retry count (initialised by processor). */
    retries?: number;
    /** Maximum number of retries before moving to dead‑letter queue. */
    maxRetries?: number;
    /** Base backoff delay in milliseconds (exponential). */
    backoffMs?: number;
}

// ------------------------------------------------------------
// Circuit Breaker Configuration
// ------------------------------------------------------------
export interface CircuitBreakerOptions {
    /** Number of consecutive failures before opening the circuit. */
    failureThreshold: number;
    /** Time window (ms) over which failures are counted. */
    timeoutMs: number;
    /** Time (ms) before attempting to close the circuit again. */
    resetTimeoutMs: number;
}

// ------------------------------------------------------------
// Circuit Breaker Implementation
// ------------------------------------------------------------
class CircuitBreaker {
    private failures = 0;
    private state: 'closed' | 'open' | 'half-open' = 'closed';
    private lastFailureTime = 0;
    private readonly options: Required<CircuitBreakerOptions>;

    constructor(options: CircuitBreakerOptions) {
        this.options = {
            failureThreshold: options.failureThreshold,
            timeoutMs: options.timeoutMs,
            resetTimeoutMs: options.resetTimeoutMs,
        };
    }

    /**
     * Execute a function through the circuit breaker.
     * @throws Error if circuit is open and not yet reset.
     */
    async call<T>(fn: () => Promise<T>): Promise<T> {
        if (this.state === 'open') {
            const now = Date.now();
            if (now - this.lastFailureTime > this.options.resetTimeoutMs) {
                this.state = 'half-open';
                console.log(`[CircuitBreaker] Half‑open – testing`);
            } else {
                throw new Error('Circuit breaker is open');
            }
        }

        try {
            const result = await fn();
            if (this.state === 'half-open') {
                this.state = 'closed';
                this.failures = 0;
                console.log(`[CircuitBreaker] Closed (recovered)`);
            }
            return result;
        } catch (err) {
            this.failures++;
            this.lastFailureTime = Date.now();

            if (this.state === 'half-open') {
                this.state = 'open';
                console.log(`[CircuitBreaker] Half‑open test failed – reopened`);
            } else if (this.failures >= this.options.failureThreshold) {
                this.state = 'open';
                console.log(`[CircuitBreaker] Opened after ${this.failures} failures`);
            }
            throw err;
        }
    }

    /** Reset the circuit breaker manually (e.g., after system recovery). */
    reset(): void {
        this.state = 'closed';
        this.failures = 0;
        console.log(`[CircuitBreaker] Manually reset`);
    }
}

// ------------------------------------------------------------
// Frictionless Task Processor
// ------------------------------------------------------------
export interface FrictionlessProcessorEvents {
    success: (payload: { taskId: string; result: any }) => void;
    failure: (payload: { taskId: string; error: Error }) => void;
    retry: (payload: { taskId: string; retry: number; error: Error; delayMs: number }) => void;
    drain: () => void;
}

export declare interface FrictionlessProcessor {
    on<E extends keyof FrictionlessProcessorEvents>(
        event: E,
        listener: FrictionlessProcessorEvents[E]
    ): this;
    emit<E extends keyof FrictionlessProcessorEvents>(
        event: E,
        ...args: Parameters<FrictionlessProcessorEvents[E]>
    ): boolean;
}

/**
 * A resilient task processor that executes asynchronous tasks with:
 * - Configurable concurrency limit.
 * - Exponential backoff retries with per‑task limits.
 * - Circuit breaker to protect downstream services.
 * - Dead‑letter queue for permanently failed tasks.
 * - Event‑driven interface for monitoring.
 */
export class FrictionlessProcessor extends EventEmitter {
    private queue: Task[] = [];
    private activeTasks = 0;
    private deadLetterQueue: Task[] = [];
    private circuitBreaker: CircuitBreaker;
    private readonly concurrency: number;
    private isProcessing = false;

    constructor(concurrency = 5, circuitBreakerOptions?: CircuitBreakerOptions) {
        super();
        this.concurrency = Math.max(1, concurrency);
        const defaultOptions: CircuitBreakerOptions = {
            failureThreshold: 3,
            timeoutMs: 60_000,
            resetTimeoutMs: 30_000,
        };
        this.circuitBreaker = new CircuitBreaker(circuitBreakerOptions ?? defaultOptions);
    }

    /**
     * Add a task to the processing queue.
     * Task will be retried up to `maxRetries` times with exponential backoff.
     */
    addTask(task: Task): void {
        // Normalise optional fields
        const normalizedTask: Task = {
            ...task,
            retries: task.retries ?? 0,
            maxRetries: task.maxRetries ?? 3,
            backoffMs: task.backoffMs ?? 1000,
        };
        this.queue.push(normalizedTask);
        this._process();
    }

    /** Start processing the queue (called automatically). */
    private async _process(): Promise<void> {
        if (this.isProcessing) return;
        this.isProcessing = true;

        while (this.activeTasks < this.concurrency && this.queue.length > 0) {
            const task = this.queue.shift()!;
            this.activeTasks++;
            // Process without awaiting (fire and forget)
            this._executeTask(task).finally(() => {
                this.activeTasks--;
                if (this.activeTasks === 0 && this.queue.length === 0) {
                    this.emit('drain');
                }
                this._process(); // continue processing
            });
        }
        this.isProcessing = false;
    }

    /** Execute a single task with circuit breaker and retry logic. */
    private async _executeTask(task: Task): Promise<void> {
        try {
            const result = await this.circuitBreaker.call(() => task.execute());
            this.emit('success', { taskId: task.id, result });
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err));
            if ((task.retries ?? 0) < (task.maxRetries ?? 0)) {
                const nextRetry = (task.retries ?? 0) + 1;
                const delay = (task.backoffMs ?? 1000) * Math.pow(2, nextRetry - 1);
                this.emit('retry', {
                    taskId: task.id,
                    retry: nextRetry,
                    error,
                    delayMs: delay,
                });
                // Re‑enqueue with updated retry count after delay
                setTimeout(() => {
                    this.queue.unshift({ ...task, retries: nextRetry });
                    this._process();
                }, delay);
            } else {
                // Permanently failed – move to dead‑letter queue
                this.deadLetterQueue.push(task);
                this.emit('failure', { taskId: task.id, error });
            }
        }
    }

    /** Get current statistics of the processor. */
    getStats(): {
        queueLength: number;
        activeTasks: number;
        deadLetterLength: number;
        concurrency: number;
        circuitBreakerState: string;
    } {
        return {
            queueLength: this.queue.length,
            activeTasks: this.activeTasks,
            deadLetterLength: this.deadLetterQueue.length,
            concurrency: this.concurrency,
            circuitBreakerState: (this.circuitBreaker as any).state, // access private for demo
        };
    }

    /** Reset the circuit breaker manually. */
    resetCircuitBreaker(): void {
        this.circuitBreaker.reset();
    }

    /** Clear the dead‑letter queue (e.g., after manual inspection). */
    clearDeadLetterQueue(): void {
        this.deadLetterQueue = [];
        this.emit('drain'); // optional
    }
}

// ------------------------------------------------------------
// Example Usage (Proof Validation)
// ------------------------------------------------------------
if (require.main === module) {
    // Mock proof verification API (replace with real Rust worker call)
    const someVerificationAPI = async (proofData: any): Promise<boolean> => {
        // Simulate 80% success rate for demonstration
        await new Promise(resolve => setTimeout(resolve, 100));
        return Math.random() < 0.8;
    };

    const processor = new FrictionlessProcessor(10);

    processor.on('success', ({ taskId, result }) => {
        console.log(`✅ Proof ${taskId} validated`, result);
        // Here you would update on‑chain state, broadcast via WebSocket, etc.
    });

    processor.on('failure', ({ taskId, error }) => {
        console.error(`❌ Proof ${taskId} permanently failed:`, error.message);
        // Log to dead‑letter queue for manual inspection
    });

    processor.on('retry', ({ taskId, retry, error, delayMs }) => {
        console.warn(`🔄 Proof ${taskId} retry #${retry} after ${delayMs}ms – ${error.message}`);
    });

    processor.on('drain', () => {
        console.log('📭 All tasks processed. Queue empty.');
    });

    // Add a batch of proof validation tasks
    for (let i = 1; i <= 20; i++) {
        processor.addTask({
            id: `proof_${i}`,
            execute: async () => {
                const isValid = await someVerificationAPI({ id: i, data: `sample_${i}` });
                if (!isValid) throw new Error(`Verification failed for proof ${i}`);
                return { valid: true, score: 9.5, timestamp: Date.now() };
            },
            maxRetries: 3,
            backoffMs: 200,
        });
    }

    // Monitor statistics every second
    const interval = setInterval(() => {
        const stats = processor.getStats();
        console.log(`Stats: queue=${stats.queueLength}, active=${stats.activeTasks}, dlq=${stats.deadLetterLength}`);
        if (stats.queueLength === 0 && stats.activeTasks === 0) {
            clearInterval(interval);
            console.log('Processing complete.');
        }
    }, 1000);
    }
