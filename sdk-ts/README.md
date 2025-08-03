# @tour-booking/sdk

TypeScript SDK for the Tour Booking API - A framework-agnostic client with full type safety, built-in retry logic, and idempotency support.

## Features

- 🎯 **Type Safe**: Generated TypeScript types from OpenAPI specification
- 🔄 **Retry Logic**: Built-in exponential backoff with jitter for retryable errors
- 🔑 **Idempotency**: Automatic idempotency key management for safe retries
- 🌐 **Framework Agnostic**: Works with any Node.js application (supports both native fetch and undici)
- 📊 **Observability**: Request/response tracing with W3C trace context support
- 🚀 **Zero Heavy Dependencies**: Minimal runtime dependencies for faster installs
- 📋 **Problem Details**: RFC 7807 compliant error handling
- ⏱️ **Timeout Support**: Configurable request timeouts with proper cancellation

## Installation

```bash
# Using npm
npm install @tour-booking/sdk

# Using yarn  
yarn add @tour-booking/sdk

# Using bun
bun add @tour-booking/sdk
```

## Quick Start

```typescript
import { Client } from '@tour-booking/sdk';

const client = new Client({
  baseUrl: 'https://api.example.com',
  token: 'your-bearer-token'
});

// Create a tour
const tour = await client.createTour({
  name: 'Northern Lights Adventure',
  slug: 'northern-lights-adventure', 
  description: 'Experience the magical Aurora Borealis in Iceland'
});

// Search departures
const departures = await client.searchDepartures({
  tour_id: tour.data.id,
  available_only: true
});

// Book seats (hold -> confirm flow)
const hold = await client.createHold({
  departure_id: departures.data.items[0].id,
  seats: 2,
  customer_ref: 'customer-123'
});

const booking = await client.confirmBooking({
  hold_id: hold.data.id
});

console.log('Booking confirmed:', booking.data.code);
```

## Configuration

### Client Options

```typescript
const client = new Client({
  baseUrl: 'https://api.example.com',     // Required: API base URL
  token: 'your-bearer-token',             // Required: Authentication token
  fetch: customFetch,                     // Optional: Custom fetch implementation
  timeoutMs: 30000,                       // Optional: Request timeout (default: 30000)
  debug: true,                            // Optional: Enable request logging (default: false)
  defaultHeaders: {                       // Optional: Additional headers for all requests
    'X-Custom-Header': 'value'
  },
  retryConfig: {                          // Optional: Retry configuration
    maxAttempts: 3,
    baseDelayMs: 100,
    maxDelayMs: 5000
  }
});
```

### Per-Request Options

```typescript
// Most methods accept optional CallOptions
await client.searchDepartures(request, {
  timeoutMs: 10000,                      // Override timeout for this request
  requestId: 'custom-request-id',        // Custom request ID for tracing
  traceparent: '00-trace-id-span-id-01', // W3C trace context
  headers: {                             // Additional headers for this request
    'X-Priority': 'high'
  },
  noRetry: true                          // Disable retry for this request
});

// Idempotent methods accept IdempotentCallOptions
await client.createHold(request, {
  idempotencyKey: 'custom-key',          // Custom idempotency key
  // ... all CallOptions also available
});
```

## API Methods

### Tours

```typescript
// Create a tour (idempotent)
const tour = await client.createTour({
  name: 'Adventure Tour',
  slug: 'adventure-tour',
  description: 'An exciting adventure'
});
```

### Departures

```typescript
// Create a departure (idempotent)
const departure = await client.createDeparture({
  tour_id: 'tour_123',
  starts_at: '2024-12-15T09:00:00Z',
  capacity_total: 40,
  price: { amount: 29999, currency: 'USD' }
});

// Search departures
const results = await client.searchDepartures({
  tour_id: 'tour_123',
  date_from: '2024-12-01',
  date_to: '2024-12-31',
  available_only: true,
  limit: 20
});
```

### Booking Flow

```typescript
// 1. Hold seats (idempotent)
const hold = await client.createHold({
  departure_id: 'dep_123',
  seats: 2,
  customer_ref: 'customer-123',
  ttl_seconds: 600 // 10 minutes
});

// 2. Confirm booking (idempotent)
const booking = await client.confirmBooking({
  hold_id: hold.data.id
});

// 3. Get booking details  
const bookingDetails = await client.getBooking({
  booking_id: booking.data.id
});

// 4. Cancel if needed (idempotent)
const cancelled = await client.cancelBooking({
  booking_id: booking.data.id
});
```

### Waitlist

```typescript
// Join waitlist when departure is full (idempotent)
const waitlistEntry = await client.joinWaitlist({
  departure_id: 'dep_123',
  customer_ref: 'customer-123'
});
```

### Inventory Management

```typescript
// Adjust capacity (idempotent)
const adjustment = await client.adjustInventory({
  departure_id: 'dep_123',
  delta: 10,
  reason: 'Upgraded to larger bus'
});
```

### Health Check

```typescript
// Health check (no authentication required)
const health = await client.healthPing();
console.log('Service status:', health.data.status);
```

## Error Handling

The SDK provides comprehensive error handling with typed error classes:

```typescript
import { isApiError, isNetworkError, ApiError } from '@tour-booking/sdk';

try {
  await client.createHold(request);
} catch (error) {
  if (isApiError(error)) {
    console.log('API Error:', {
      status: error.status,
      code: error.code,
      detail: error.detailMessage,
      traceId: error.traceId,
      retryable: error.retryable
    });
    
    // Handle specific error codes
    switch (error.code) {
      case 'FULL':
        // Departure is full, suggest waitlist
        await client.joinWaitlist(waitlistRequest);
        break;
      case 'HOLD_EXPIRED':  
        // Hold expired, create new one
        await client.createHold(holdRequest);
        break;
    }
  } else if (isNetworkError(error)) {
    console.log('Network Error:', error.message, 'Retryable:', error.retryable);
  } else {
    console.log('Unexpected error:', error);
  }
}
```

### Error Types

- **ApiError**: Server returned an error response (4xx/5xx)
- **NetworkError**: Network-level failures (timeouts, connection errors)
- **ClientError**: Client configuration errors
- **TimeoutError**: Request timed out
- **IdempotencyError**: Idempotency key conflict
- **ValidationError**: Request validation failures

## Idempotency

The SDK automatically handles idempotency for safe operations:

```typescript
// Automatic idempotency key generation
const hold1 = await client.createHold(request);
const hold2 = await client.createHold(request); // Different key, creates new hold

// Manual idempotency key (recommended for retry scenarios)
const key = generateIdempotencyKey();
const hold1 = await client.createHold(request, { idempotencyKey: key });
const hold2 = await client.createHold(request, { idempotencyKey: key }); // Same response
```

## Retry Logic

Built-in retry with exponential backoff and jitter:

```typescript
// Default retry behavior
const response = await client.searchDepartures(request);

// Custom retry configuration
const response = await client.searchDepartures(request, {
  retryConfig: {
    maxAttempts: 5,
    baseDelayMs: 200,
    maxDelayMs: 10000
  }
});

// Disable retry for specific requests
const response = await client.searchDepartures(request, {
  noRetry: true
});
```

## Tracing and Observability

The SDK supports distributed tracing and request correlation:

```typescript
// Automatic request ID generation
const response = await client.createTour(request);
console.log('Request ID:', response.requestId);
console.log('Trace ID:', response.traceId);

// Custom request ID and trace context
const response = await client.createTour(request, {
  requestId: 'my-request-id',
  traceparent: '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01'
});

// Enable debug logging
const client = new Client({
  baseUrl: 'https://api.example.com',
  token: 'token',
  debug: true // Logs all requests/responses
});
```

## Convenience Methods

The SDK includes convenience methods for common workflows:

```typescript
// Create tour + departure in one call
const { tour, departure } = await client.createTourWithDeparture(
  tourRequest,
  departureRequest
);

// Hold + confirm in one call  
const { hold, booking } = await client.holdAndConfirmBooking(holdRequest);
```

## TypeScript Support

Full TypeScript support with generated types from OpenAPI:

```typescript
import type { 
  CreateTourRequest,
  Tour,
  Departure,
  Booking,
  Money,
  Problem 
} from '@tour-booking/sdk';

// All request/response types are fully typed
const tourRequest: CreateTourRequest = {
  name: 'Adventure Tour',
  slug: 'adventure-tour', 
  description: 'An exciting adventure'
};

const tour: Tour = (await client.createTour(tourRequest)).data;
```

## Node.js Compatibility

- **Node.js**: 18+ (requires fetch support)
- **TypeScript**: 4.5+
- **Fetch**: Uses global fetch or custom implementation

```typescript
// Using with undici (recommended for Node.js < 18)
import { fetch } from 'undici';

const client = new Client({
  baseUrl: 'https://api.example.com',
  token: 'token',
  fetch
});
```

## Examples

See the [examples/](examples/) directory for more comprehensive usage examples:

- [basic-usage.ts](examples/basic-usage.ts) - Complete booking flow example

## Development

```bash
# Install dependencies
bun install

# Generate types from OpenAPI spec
bun run generate-types

# Build the SDK
bun run build

# Run tests
bun run test

# Type check
bun run typecheck

# Lint code
bun run lint
```

## License

MIT