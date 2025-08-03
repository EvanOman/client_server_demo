import { ApiError, NetworkError, TimeoutError, isRetryableError } from './errors.js';
import { Problem } from './errors.js';

/**
 * Generate a UUID v4 string
 */
export function generateUuid(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  
  // Fallback for older Node.js versions
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Generate a random idempotency key
 */
export function generateIdempotencyKey(): string {
  return generateUuid();
}

/**
 * Sleep for a given number of milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay with jitter
 */
export function calculateBackoffDelay(attempt: number, baseDelayMs = 100, maxDelayMs = 5000): number {
  const exponentialDelay = Math.min(baseDelayMs * Math.pow(2, attempt), maxDelayMs);
  const jitter = Math.random() * 0.1 * exponentialDelay; // 10% jitter
  return Math.floor(exponentialDelay + jitter);
}

/**
 * Retry configuration
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Base delay between retries in milliseconds */
  baseDelayMs: number;
  /** Maximum delay between retries in milliseconds */
  maxDelayMs: number;
  /** Custom predicate to determine if an error should be retried */
  shouldRetry?: (error: any, attempt: number) => boolean;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  baseDelayMs: 100,
  maxDelayMs: 5000,
  shouldRetry: (error: any, attempt: number) => {
    // Don't retry client errors (4xx) except for specific cases
    if (error instanceof ApiError) {
      const status = error.status;
      // Retry on server errors (5xx) and rate limits (429)
      if (status >= 500 || status === 429) {
        return true;
      }
      // Don't retry client errors
      if (status >= 400 && status < 500) {
        return false;
      }
    }
    
    // Retry network errors that are marked as retryable
    return isRetryableError(error) && attempt < 3;
  },
};

/**
 * Retry a function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: any;

  for (let attempt = 0; attempt < finalConfig.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Check if we should retry this error
      if (!finalConfig.shouldRetry?.(error, attempt)) {
        throw error;
      }

      // Don't wait after the last attempt
      if (attempt < finalConfig.maxAttempts - 1) {
        const delay = calculateBackoffDelay(attempt, finalConfig.baseDelayMs, finalConfig.maxDelayMs);
        await sleep(delay);
      }
    }
  }

  throw lastError;
}

/**
 * Create a fetch function with timeout support
 */
export function createTimeoutFetch(
  fetchFn: typeof fetch,
  timeoutMs: number
): typeof fetch {
  return async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetchFn(input, {
        ...init,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === 'AbortError') {
        throw new TimeoutError(timeoutMs);
      }
      
      throw new NetworkError(
        `Network request failed: ${error instanceof Error ? error.message : String(error)}`,
        error instanceof Error ? error : undefined
      );
    }
  };
}

/**
 * Parse Problem Details from response
 */
export async function parseProblemDetails(response: Response): Promise<Problem> {
  let problemData: any = {};

  try {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/problem+json') || contentType.includes('application/json')) {
      problemData = await response.json();
    }
  } catch {
    // If JSON parsing fails, we'll use default values
  }

  return {
    title: problemData.title || response.statusText || 'Unknown Error',
    status: problemData.status || response.status,
    type: problemData.type,
    detail: problemData.detail,
    instance: problemData.instance,
    code: problemData.code,
    retryable: problemData.retryable,
    trace_id: problemData.trace_id,
    violations: problemData.violations,
  };
}

/**
 * Build headers for API requests
 */
export function buildHeaders(options: {
  token?: string;
  idempotencyKey?: string;
  requestId?: string;
  traceparent?: string;
  additionalHeaders?: Record<string, string>;
}): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  if (options.token) {
    headers['Authorization'] = `Bearer ${options.token}`;
  }

  if (options.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey;
  }

  if (options.requestId) {
    headers['x-request-id'] = options.requestId;
  }

  if (options.traceparent) {
    headers['traceparent'] = options.traceparent;
  }

  // Add any additional headers
  if (options.additionalHeaders) {
    Object.assign(headers, options.additionalHeaders);
  }

  return headers;
}

/**
 * Validate that required options are present
 */
export function validateRequiredOptions(options: Record<string, any>, required: string[]): void {
  const missing = required.filter(key => 
    options[key] === undefined || options[key] === null || options[key] === ''
  );

  if (missing.length > 0) {
    throw new Error(`Missing required options: ${missing.join(', ')}`);
  }
}

/**
 * Serialize request body for consistent hashing
 */
export function serializeRequestBody(body: any): string {
  if (body === null || body === undefined) {
    return '';
  }
  
  if (typeof body === 'string') {
    return body;
  }

  // Sort object keys for consistent serialization
  return JSON.stringify(body, Object.keys(body).sort());
}

/**
 * Extract trace ID from response headers
 */
export function extractTraceId(response: Response): string | undefined {
  return response.headers.get('x-trace-id') || 
         response.headers.get('trace-id') ||
         undefined;
}

/**
 * Check if a method is idempotent based on OpenAPI extensions
 */
export function isIdempotentMethod(method: string): boolean {
  // These methods are marked as idempotent in the OpenAPI spec
  const idempotentMethods = new Set([
    'createTour',
    'createDeparture', 
    'createHold',
    'confirmBooking',
    'cancelBooking',
    'joinWaitlist',
    'notifyWaitlist',
    'adjustInventory'
  ]);

  return idempotentMethods.has(method);
}

/**
 * Create a standard User-Agent header
 */
export function createUserAgent(version: string): string {
  const nodeVersion = typeof process !== 'undefined' ? process.version : 'unknown';
  return `@tour-booking/sdk/${version} (Node.js ${nodeVersion})`;
}