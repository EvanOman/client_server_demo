/**
 * @tour-booking/sdk - TypeScript SDK for Tour Booking API
 * 
 * A framework-agnostic TypeScript client for the Tour Booking API with:
 * - Generated types from OpenAPI specification
 * - Built-in retry logic with exponential backoff
 * - Idempotency key management
 * - Request/response tracing support
 * - Problem Details (RFC 7807) error handling
 * - Zero heavy dependencies
 * 
 * @example
 * ```typescript
 * import { Client } from '@tour-booking/sdk';
 * 
 * const client = new Client({
 *   baseUrl: 'https://api.example.com',
 *   token: 'your-bearer-token'
 * });
 * 
 * // Create a tour
 * const tour = await client.createTour({
 *   name: 'Northern Lights Adventure',
 *   slug: 'northern-lights-adventure',
 *   description: 'Experience the magical Aurora Borealis in Iceland'
 * });
 * 
 * // Search departures
 * const departures = await client.searchDepartures({
 *   tour_id: tour.data.id,
 *   available_only: true
 * });
 * 
 * // Hold seats
 * const hold = await client.createHold({
 *   departure_id: departures.data.items[0].id,
 *   seats: 2,
 *   customer_ref: 'customer-123'
 * });
 * 
 * // Confirm booking
 * const booking = await client.confirmBooking({
 *   hold_id: hold.data.id
 * });
 * ```
 */

// Main client export
export { Client } from './client.js';

// Client types and interfaces
export type {
  ClientOptions,
  CallOptions,
  IdempotentCallOptions,
  ApiResponse,
  
  // Request/Response types
  CreateTourRequest,
  CreateTourResponse,
  CreateDepartureRequest,
  CreateDepartureResponse,
  SearchDeparturesRequest,
  SearchDeparturesResponse,
  CreateHoldRequest,
  CreateHoldResponse,
  ConfirmBookingRequest,
  ConfirmBookingResponse,
  CancelBookingRequest,
  CancelBookingResponse,
  GetBookingRequest,
  GetBookingResponse,
  JoinWaitlistRequest,
  JoinWaitlistResponse,
  NotifyWaitlistRequest,
  NotifyWaitlistResponse,
  AdjustInventoryRequest,
  AdjustInventoryResponse,
  HealthPingResponse,
} from './client.js';

// Error classes
export {
  ApiError,
  NetworkError,
  ClientError,
  TimeoutError,
  IdempotencyError,
  ValidationError,
  
  // Error type guards
  isApiError,
  isNetworkError,
  isRetryableError,
} from './errors.js';

// Problem Details type
export type { Problem } from './errors.js';

// Utility functions
export {
  generateUuid,
  generateIdempotencyKey,
  sleep,
  calculateBackoffDelay,
  retry,
  createTimeoutFetch,
  buildHeaders,
  parseProblemDetails,
  isIdempotentMethod,
  createUserAgent,
} from './utils.js';

// Utility types
export type { RetryConfig } from './utils.js';

// Re-export selected OpenAPI generated types for external use
export type {
  components,
} from './types.js';

// Common domain types that users might need
export type Money = components['schemas']['Money'];
export type Tour = components['schemas']['Tour'];
export type Departure = components['schemas']['Departure'];
export type Hold = components['schemas']['Hold'];
export type Booking = components['schemas']['Booking'];
export type WaitlistEntry = components['schemas']['WaitlistEntry'];
export type InventoryAdjustment = components['schemas']['InventoryAdjustment'];
export type HealthResponse = components['schemas']['HealthResponse'];

// Import the generated types to ensure they're available
import type { components } from './types.js';

/**
 * SDK version - should match package.json
 * TODO: This should be dynamically imported from package.json in build
 */
export const VERSION = '0.1.0';

/**
 * Default configuration values
 */
export const DEFAULTS = {
  TIMEOUT_MS: 30000,
  MAX_RETRY_ATTEMPTS: 3,
  BASE_RETRY_DELAY_MS: 100,
  MAX_RETRY_DELAY_MS: 5000,
} as const;

// Import ClientOptions and Client for the factory function
import type { ClientOptions } from './client.js';
import { Client } from './client.js';

/**
 * Create a new client instance with the given options
 * 
 * @param options - Client configuration
 * @returns Configured client instance
 * 
 * @example
 * ```typescript
 * const client = createClient({
 *   baseUrl: process.env.API_BASE_URL!,
 *   token: process.env.API_TOKEN!,
 *   debug: process.env.NODE_ENV === 'development'
 * });
 * ```
 */
export function createClient(options: ClientOptions): Client {
  return new Client(options);
}