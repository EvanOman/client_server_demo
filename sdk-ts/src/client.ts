import { components } from './types.js';
import { 
  ApiError, 
  ClientError, 
  IdempotencyError
} from './errors.js';
import {
  buildHeaders,
  createTimeoutFetch,
  parseProblemDetails,
  retry,
  generateIdempotencyKey, 
  generateUuid,
  validateRequiredOptions,
  extractTraceId,
  createUserAgent,
  RetryConfig,
  DEFAULT_RETRY_CONFIG
} from './utils.js';

// Extract types from the generated OpenAPI types
export type CreateTourRequest = components['schemas']['CreateTourRequest'];
export type CreateTourResponse = components['schemas']['Tour'];

export type CreateDepartureRequest = components['schemas']['CreateDepartureRequest'];
export type CreateDepartureResponse = components['schemas']['Departure'];

export type SearchDeparturesRequest = components['schemas']['SearchDeparturesRequest'];
export type SearchDeparturesResponse = components['schemas']['SearchDeparturesResponse'];

export type CreateHoldRequest = components['schemas']['CreateHoldRequest'];
export type CreateHoldResponse = components['schemas']['Hold'];

export type ConfirmBookingRequest = components['schemas']['ConfirmBookingRequest'];
export type ConfirmBookingResponse = components['schemas']['Booking'];

export type CancelBookingRequest = components['schemas']['CancelBookingRequest'];
export type CancelBookingResponse = components['schemas']['Booking'];

export type GetBookingRequest = components['schemas']['GetBookingRequest'];
export type GetBookingResponse = components['schemas']['Booking'];

export type JoinWaitlistRequest = components['schemas']['JoinWaitlistRequest'];
export type JoinWaitlistResponse = components['schemas']['WaitlistEntry'];

export type NotifyWaitlistRequest = components['schemas']['NotifyWaitlistRequest'];
export type NotifyWaitlistResponse = components['schemas']['NotifyWaitlistResponse'];

export type AdjustInventoryRequest = components['schemas']['AdjustInventoryRequest'];
export type AdjustInventoryResponse = components['schemas']['InventoryAdjustment'];

export type HealthPingResponse = components['schemas']['HealthResponse'];

/**
 * Client configuration options
 */
export interface ClientOptions {
  /** Base URL for the API (e.g., 'https://api.example.com') */
  baseUrl: string;
  /** Bearer token for authentication */
  token: string;
  /** Custom fetch implementation (defaults to global fetch) */
  fetch?: typeof fetch;
  /** Request timeout in milliseconds (default: 30000) */
  timeoutMs?: number;
  /** Retry configuration for failed requests */
  retryConfig?: Partial<RetryConfig>;
  /** Additional headers to include with every request */
  defaultHeaders?: Record<string, string>;
  /** Enable request/response logging */
  debug?: boolean;
}

/**
 * Options for individual API method calls
 */
export interface CallOptions {
  /** Override the default timeout for this request */
  timeoutMs?: number;
  /** Additional headers for this request */
  headers?: Record<string, string>;
  /** Custom request ID (generated if not provided) */
  requestId?: string;
  /** W3C trace parent header */
  traceparent?: string;
  /** Override retry configuration for this request */
  retryConfig?: Partial<RetryConfig>;
  /** Disable retry for this request */
  noRetry?: boolean;
}

/**
 * Options for idempotent operations
 */
export interface IdempotentCallOptions extends CallOptions {
  /** Idempotency key (generated if not provided) */
  idempotencyKey?: string;
}

/**
 * Response wrapper that includes metadata
 */
export interface ApiResponse<T> {
  /** The response data */
  data: T;
  /** HTTP status code */
  status: number;
  /** Response headers */
  headers: Record<string, string>;
  /** Request ID from response */
  requestId?: string;
  /** Trace ID from response */
  traceId?: string;
  /** Request duration in milliseconds */
  duration: number;
}

/**
 * Main client class for the Tour Booking API
 */
export class Client {
  private readonly baseUrl: string;
  private readonly token: string;
  private readonly fetchFn: typeof fetch;
  private readonly timeoutMs: number;
  private readonly retryConfig: RetryConfig;
  private readonly defaultHeaders: Record<string, string>;
  private readonly debug: boolean;
  private readonly userAgent: string;

  constructor(options: ClientOptions) {
    validateRequiredOptions(options, ['baseUrl', 'token']);

    this.baseUrl = options.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.token = options.token;
    this.timeoutMs = options.timeoutMs ?? 30000;
    this.retryConfig = { ...DEFAULT_RETRY_CONFIG, ...options.retryConfig };
    this.defaultHeaders = options.defaultHeaders ?? {};
    this.debug = options.debug ?? false;
    this.userAgent = createUserAgent('0.1.0'); // TODO: Read from package.json

    // Use provided fetch or try to find one
    if (options.fetch) {
      this.fetchFn = options.fetch;
    } else if (typeof fetch !== 'undefined') {
      this.fetchFn = fetch;
    } else {
      throw new ClientError(
        'No fetch implementation available. Please provide one via options.fetch or ensure global fetch is available.'
      );
    }
  }

  /**
   * Make a raw HTTP request
   */
  private async makeRequest<T>(
    path: string,
    method: 'POST' = 'POST',
    body?: any,
    options: CallOptions = {}
  ): Promise<ApiResponse<T>> {
    const startTime = Date.now();
    const requestId = options.requestId || generateUuid();
    const url = `${this.baseUrl}${path}`;

    const headers = buildHeaders({
      token: this.token,
      requestId,
      traceparent: options.traceparent,
      additionalHeaders: {
        'User-Agent': this.userAgent,
        ...this.defaultHeaders,
        ...options.headers,
      },
    });

    const requestOptions: RequestInit = {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    };

    if (this.debug) {
      console.log(`[SDK] ${method} ${url}`, {
        headers,
        body,
        requestId,
      });
    }

    const timeoutFetch = createTimeoutFetch(
      this.fetchFn,
      options.timeoutMs ?? this.timeoutMs
    );

    try {
      const response = await timeoutFetch(url, requestOptions);
      const duration = Date.now() - startTime;

      // Convert headers to plain object
      const responseHeaders: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });

      const responseRequestId = responseHeaders['x-request-id'] || requestId;
      const traceId = extractTraceId(response);

      if (this.debug) {
        console.log(`[SDK] Response ${response.status}`, {
          requestId: responseRequestId,
          traceId,
          duration,
          headers: responseHeaders,
        });
      }

      // Handle error responses
      if (!response.ok) {
        const problem = await parseProblemDetails(response);
        
        if (problem.code === 'IDEMPOTENCY_KEY_MISMATCH') {
          throw new IdempotencyError(problem);
        }
        
        throw new ApiError(problem);
      }

      // Parse successful response
      let data: T;
      const contentType = response.headers.get('content-type') || '';
      
      if (contentType.includes('application/json')) {
        data = await response.json() as T;
      } else {
        // For non-JSON responses, return empty object
        data = {} as T;
      }

      return {
        data,
        status: response.status,
        headers: responseHeaders,
        requestId: responseRequestId,
        traceId,
        duration,
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      
      if (this.debug) {
        console.error(`[SDK] Request failed`, {
          requestId,
          duration,
          error: error instanceof Error ? error.message : String(error),
        });
      }

      throw error;
    }
  }

  /**
   * Make a request with retry logic
   */
  private async makeRequestWithRetry<T>(
    path: string,
    method: 'POST' = 'POST',
    body?: any,
    options: CallOptions = {}
  ): Promise<ApiResponse<T>> {
    const retryConfig = options.noRetry ? 
      { maxAttempts: 1 } : 
      { ...this.retryConfig, ...options.retryConfig };

    return retry(
      () => this.makeRequest<T>(path, method, body, options),
      retryConfig
    );
  }

  // ==================== Tour Methods ====================

  /**
   * Create a new tour
   */
  async createTour(
    request: CreateTourRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<CreateTourResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<CreateTourResponse>(
      '/v1/tour/create',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  // ==================== Departure Methods ====================

  /**
   * Create a new departure
   */
  async createDeparture(
    request: CreateDepartureRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<CreateDepartureResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<CreateDepartureResponse>(
      '/v1/departure/create',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  /**
   * Search departures
   */
  async searchDepartures(
    request: SearchDeparturesRequest,
    options: CallOptions = {}
  ): Promise<ApiResponse<SearchDeparturesResponse>> {
    return this.makeRequestWithRetry<SearchDeparturesResponse>(
      '/v1/departure/search',
      'POST',
      request,
      options
    );
  }

  // ==================== Booking Methods ====================

  /**
   * Create or refresh a seat hold
   */
  async createHold(
    request: CreateHoldRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<CreateHoldResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<CreateHoldResponse>(
      '/v1/booking/hold',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  /**
   * Confirm a booking from a hold
   */
  async confirmBooking(
    request: ConfirmBookingRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<ConfirmBookingResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<ConfirmBookingResponse>(
      '/v1/booking/confirm',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  /**
   * Cancel a booking
   */
  async cancelBooking(
    request: CancelBookingRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<CancelBookingResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<CancelBookingResponse>(
      '/v1/booking/cancel',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  /**
   * Get booking details
   */
  async getBooking(
    request: GetBookingRequest,
    options: CallOptions = {}
  ): Promise<ApiResponse<GetBookingResponse>> {
    return this.makeRequestWithRetry<GetBookingResponse>(
      '/v1/booking/get',
      'POST',
      request,
      options
    );
  }

  // ==================== Waitlist Methods ====================

  /**
   * Join departure waitlist
   */
  async joinWaitlist(
    request: JoinWaitlistRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<JoinWaitlistResponse>> {
    // This method is idempotent by customer_ref + departure_id, no key needed
    return this.makeRequestWithRetry<JoinWaitlistResponse>(
      '/v1/waitlist/join',
      'POST',
      request,
      options
    );
  }

  /**
   * Process waitlist notifications (internal)
   */
  async notifyWaitlist(
    request: NotifyWaitlistRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<NotifyWaitlistResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<NotifyWaitlistResponse>(
      '/v1/waitlist/notify',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  // ==================== Inventory Methods ====================

  /**
   * Adjust departure capacity
   */
  async adjustInventory(
    request: AdjustInventoryRequest,
    options: IdempotentCallOptions = {}
  ): Promise<ApiResponse<AdjustInventoryResponse>> {
    const idempotencyKey = options.idempotencyKey || generateIdempotencyKey();
    
    return this.makeRequestWithRetry<AdjustInventoryResponse>(
      '/v1/inventory/adjust',
      'POST',
      request,
      {
        ...options,
        headers: {
          'Idempotency-Key': idempotencyKey,
          ...options.headers,
        },
      }
    );
  }

  // ==================== Health Methods ====================

  /**
   * Health check
   */
  async healthPing(
    options: CallOptions = {}
  ): Promise<ApiResponse<HealthPingResponse>> {
    return this.makeRequestWithRetry<HealthPingResponse>(
      '/v1/health/ping',
      'POST',
      {},
      {
        ...options,
        // Don't use auth token for health check
        headers: {
          'Authorization': '', // Override auth
          ...options.headers,
        },
      }
    );
  }

  // ==================== Convenience Methods ====================

  /**
   * Create a tour and departure in sequence
   */
  async createTourWithDeparture(
    tourRequest: CreateTourRequest,
    departureRequest: Omit<CreateDepartureRequest, 'tour_id'>,
    options: IdempotentCallOptions = {}
  ): Promise<{
    tour: ApiResponse<CreateTourResponse>;
    departure: ApiResponse<CreateDepartureResponse>;
  }> {
    const tour = await this.createTour(tourRequest, options);
    
    const departure = await this.createDeparture(
      {
        ...departureRequest,
        tour_id: tour.data.id,
      },
      options
    );

    return { tour, departure };
  }

  /**
   * Hold and immediately confirm booking
   */
  async holdAndConfirmBooking(
    holdRequest: CreateHoldRequest,
    options: IdempotentCallOptions = {}
  ): Promise<{
    hold: ApiResponse<CreateHoldResponse>;
    booking: ApiResponse<ConfirmBookingResponse>;
  }> {
    const hold = await this.createHold(holdRequest, options);
    
    const booking = await this.confirmBooking(
      { hold_id: hold.data.id },
      options
    );

    return { hold, booking };
  }
}