// frictionless.ts
import { EventEmitter } from 'events';

interface Task<T = any> {
    id: string;
    execute: () => Promise<T>;
    retries?: number;
    maxRetries?: number;
    backoffMs?: number;
}

interface CircuitBreakerOptions {
    failureThreshold: number;   // number of failures before opening
    timeoutMs: number;          // time window for failures
    resetTimeoutMs: number;     // time before attempting again
}

class CircuitBreaker {
    private failures = 0;
    private state: 'closed' | 'open' | 'half-open' = 'closed';
    private lastFailureTime = 0;

    constructor(private options: CircuitBreakerOptions) {}

    async call<T>(fn: () => Promise<T>): Promise<T> {
        if (this.state === 'open') {
            if (Date.now() - this.lastFailureTime > this.options.resetTimeoutMs) {
                this.state = 'half-open';
                console.log('Circuit breaker half-open, testing...');
            } else {
                throw new Error('Circuit breaker is open');
            }
        }

        try {
            const result = await fn();
            if (this.state === 'half-open') {
                this.state = 'closed';
                this.failures = 0;
                console.log('Circuit breaker closed');
            }
            return result;
        } catch (err) {
            this.failures++;
            this.lastFailureTime = Date.now();
            if (this.failures >= this.options.failureThreshold) {
                this.state = 'open';
                console.log('Circuit breaker opened');
            }
            throw err;
        }
    }
}

class FrictionlessProcessor extends EventEmitter {
    private queue: Task[] = [];
    private activeTasks = 0;
    private deadLetterQueue: Task[] = [];
    private circuitBreaker: CircuitBreaker;
    private concurrency: number;

    constructor(concurrency = 5, circuitBreakerOptions?: CircuitBreakerOptions) {
        super();
        this.concurrency = concurrency;
        this.circuitBreaker = new CircuitBreaker(circuitBreakerOptions || {
            failureThreshold: 3,
            timeoutMs: 60000,
            resetTimeoutMs: 30000,
        });
    }

    addTask(task: Task) {
        if (!task.maxRetries) task.maxRetries = 3;
        if (!task.backoffMs) task.backoffMs = 1000;
        if (!task.retries) task.retries = 0;
        this.queue.push(task);
        this.process();
    }

    private async process() {
        if (this.activeTasks >= this.concurrency) return;
        if (this.queue.length === 0) return;

        const task = this.queue.shift()!;
        this.activeTasks++;

        try {
            const result = await this.circuitBreaker.call(() => task.execute());
            this.emit('success', { taskId: task.id, result });
        } catch (err) {
            if (task.retries! < task.maxRetries!) {
                task.retries!++;
                const delay = task.backoffMs! * Math.pow(2, task.retries! - 1);
                setTimeout(() => {
                    this.queue.unshift(task);
                    this.process();
                }, delay);
                this.emit('retry', { taskId: task.id, retry: task.retries, error: err });
            } else {
                this.deadLetterQueue.push(task);
                this.emit('failure', { taskId: task.id, error: err });
            }
        } finally {
            this.activeTasks--;
            this.process();
        }
    }

    getStats() {
        return {
            queueLength: this.queue.length,
            activeTasks: this.activeTasks,
            deadLetterLength: this.deadLetterQueue.length,
        };
    }
}

// Example usage in Radiant Protocol (e.g., proof validation)
const processor = new FrictionlessProcessor(10); // 10 concurrent tasks

// Vital process: validate a proof
processor.on('success', ({ taskId, result }) => {
    console.log(`Proof ${taskId} validated successfully`, result);
    // Update on-chain or broadcast via WebSocket
});

processor.on('failure', ({ taskId, error }) => {
    console.error(`Proof ${taskId} failed permanently`, error);
    // Log to dead letter queue for manual inspection
});

// Simulate adding a proof validation task
function validateProof(proofId: string, proofData: any) {
    processor.addTask({
        id: proofId,
        execute: async () => {
            // Simulate proof verification (e.g., call Rust worker, Nova folding)
            const isValid = await someVerificationAPI(proofData);
            if (!isValid) throw new Error('Invalid proof');
            return { valid: true, score: 9.5 };
        },
        maxRetries: 5,
        backoffMs: 500,
    });
            }
