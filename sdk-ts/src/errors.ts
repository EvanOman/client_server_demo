import { components } from './types.js';

export type Problem = components['schemas']['Problem'];

/**
 * Base class for API errors with Problem Details format
 * @see RFC7807: https://tools.ietf.org/html/rfc7807
 */
export class ApiError extends Error {
  readonly problem: Problem;
  readonly status: number;
  readonly traceId?: string;
  readonly violations?: Array<{ path?: string; message?: string }>;

  constructor(problem: Problem) {
    super(problem.title);
    this.name = 'ApiError';
    this.problem = problem;
    this.status = problem.status;
    this.traceId = problem.trace_id;
    this.violations = problem.violations;

    // Ensure proper prototype chain
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  /**
   * Get the error code from the problem
   */
  get code(): string | undefined {
    return this.problem.code;
  }

  /**
   * Check if the error is retryable
   */
  get retryable(): boolean {
    return this.problem.retryable ?? false;
  }

  /**
   * Get detailed error message including problem details
   */
  get detailMessage(): string {
    return this.problem.detail ?? this.message;
  }

  /**
   * Convert to JSON for logging
   */
  toJSON(): Record<string, any> {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      code: this.code,
      detail: this.detailMessage,
      traceId: this.traceId,
      violations: this.violations,
      retryable: this.retryable,
    };
  }
}

/**
 * Network-level error (timeouts, connection failures, etc.)
 */
export class NetworkError extends Error {
  readonly cause?: Error;
  readonly retryable: boolean;

  constructor(message: string, cause?: Error, retryable = true) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
    this.retryable = retryable;

    Object.setPrototypeOf(this, NetworkError.prototype);
  }

  toJSON(): Record<string, any> {
    return {
      name: this.name,
      message: this.message,
      retryable: this.retryable,
      cause: this.cause?.message,
    };
  }
}

/**
 * Client configuration error
 */
export class ClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ClientError';

    Object.setPrototypeOf(this, ClientError.prototype);
  }
}

/**
 * Error thrown when timeout is exceeded
 */
export class TimeoutError extends NetworkError {
  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = 'TimeoutError';

    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

/**
 * Error thrown when an idempotency key conflict occurs
 */
export class IdempotencyError extends ApiError {
  constructor(problem: Problem) {
    super(problem);
    this.name = 'IdempotencyError';

    Object.setPrototypeOf(this, IdempotencyError.prototype);
  }

  static isIdempotencyError(error: any): error is IdempotencyError {
    return error instanceof IdempotencyError || 
           (error instanceof ApiError && error.code === 'IDEMPOTENCY_KEY_MISMATCH');
  }
}

/**
 * Error thrown when required parameters are missing
 */
export class ValidationError extends Error {
  readonly violations: Array<{ path?: string; message?: string }>;

  constructor(violations: Array<{ path?: string; message?: string }>) {
    const message = violations.length === 1 
      ? `Validation error: ${violations[0].message}` 
      : `Validation errors: ${violations.length} violations`;
    
    super(message);
    this.name = 'ValidationError';
    this.violations = violations;

    Object.setPrototypeOf(this, ValidationError.prototype);
  }

  toJSON(): Record<string, any> {
    return {
      name: this.name,
      message: this.message,
      violations: this.violations,
    };
  }
}

/**
 * Type guard to check if an error is an ApiError
 */
export function isApiError(error: any): error is ApiError {
  return error instanceof ApiError;
}

/**
 * Type guard to check if an error is a NetworkError
 */
export function isNetworkError(error: any): error is NetworkError {
  return error instanceof NetworkError;
}

/**
 * Type guard to check if an error is retryable
 */
export function isRetryableError(error: any): boolean {
  if (isApiError(error) || isNetworkError(error)) {
    return error.retryable;
  }
  return false;
}