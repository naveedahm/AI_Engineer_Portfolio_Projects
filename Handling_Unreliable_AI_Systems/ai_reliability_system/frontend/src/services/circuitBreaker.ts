interface CircuitBreakerOptions {
  failureThreshold: number;
  timeout: number;
  halfOpenTimeout: number;
}

export class CircuitBreaker {
  private failures = 0;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private lastFailureTime: number | null = null;
  private readonly options: CircuitBreakerOptions;

  constructor(options?: Partial<CircuitBreakerOptions>) {
    this.options = {
      failureThreshold: 5,
      timeout: 60000,
      halfOpenTimeout: 30000,
      ...options
    };
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (!this.canExecute()) {
      throw new Error(`Circuit breaker is ${this.state}`);
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private canExecute(): boolean {
    if (this.state === 'CLOSED') {
      return true;
    }

    if (this.state === 'OPEN') {
      if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.options.timeout) {
        this.state = 'HALF_OPEN';
        return true;
      }
      return false;
    }

    return true; // HALF_OPEN state allows execution
  }

  private onSuccess(): void {
    if (this.state === 'HALF_OPEN') {
      this.reset();
    }
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.options.failureThreshold) {
      this.state = 'OPEN';
    }
  }

  private reset(): void {
    this.failures = 0;
    this.state = 'CLOSED';
    this.lastFailureTime = null;
  }

  getState(): string {
    return this.state;
  }
}

// React hook for using circuit breaker
import { useRef, useCallback } from 'react';

export const useCircuitBreaker = (options?: Partial<CircuitBreakerOptions>) => {
  const breakerRef = useRef<CircuitBreaker>(new CircuitBreaker(options));

  const execute = useCallback(async <T>(fn: () => Promise<T>): Promise<T> => {
    return breakerRef.current.execute(fn);
  }, []);

  const getState = useCallback(() => {
    return breakerRef.current.getState();
  }, []);

  return {
    execute,
    getState,
    state: getState()
  };
};