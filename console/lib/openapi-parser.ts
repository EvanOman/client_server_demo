import { ApiMethod } from '@/app/components/method-picker'

export interface SchemaProperty {
  type: string
  format?: string
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
  pattern?: string
  enum?: string[]
  items?: SchemaProperty
  properties?: Record<string, SchemaProperty>
  required?: string[]
  description?: string
  default?: any
  example?: any
}

export interface RequestSchema {
  type: 'object'
  properties: Record<string, SchemaProperty>
  required: string[]
}

export interface ResponseSchema {
  status: number
  description: string
  schema?: SchemaProperty
  example?: any
}

export interface MethodSchema {
  method: ApiMethod
  requestSchema?: RequestSchema
  requestExample?: any
  responses: ResponseSchema[]
  requiresIdempotencyKey?: boolean
  requiresAuth?: boolean
}

// Schema definitions based on the OpenAPI spec
const schemas = {
  CreateTourRequest: {
    type: 'object',
    required: ['name', 'slug', 'description'],
    properties: {
      name: {
        type: 'string',
        minLength: 1,
        maxLength: 255,
        description: 'Tour name',
      },
      slug: {
        type: 'string',
        pattern: '^[a-z0-9-]+$',
        minLength: 1,
        maxLength: 255,
        description: 'URL-friendly slug',
      },
      description: {
        type: 'string',
        minLength: 1,
        maxLength: 2000,
        description: 'Tour description',
      },
    },
  },
  CreateDepartureRequest: {
    type: 'object',
    required: ['tour_id', 'starts_at', 'capacity_total', 'price'],
    properties: {
      tour_id: {
        type: 'string',
        description: 'Associated tour ID',
      },
      starts_at: {
        type: 'string',
        format: 'date-time',
        description: 'Departure start time (ISO 8601)',
      },
      capacity_total: {
        type: 'integer',
        minimum: 1,
        maximum: 1000,
        description: 'Total capacity',
      },
      price: {
        type: 'object',
        required: ['amount', 'currency'],
        properties: {
          amount: {
            type: 'integer',
            minimum: 0,
            description: 'Amount in minor units (e.g., cents)',
          },
          currency: {
            type: 'string',
            minLength: 3,
            maxLength: 3,
            pattern: '^[A-Z]{3}$',
            description: 'ISO 4217 currency code',
          },
        },
      },
    },
  },
  SearchDeparturesRequest: {
    type: 'object',
    properties: {
      tour_id: {
        type: 'string',
        description: 'Filter by tour ID',
      },
      date_from: {
        type: 'string',
        format: 'date',
        description: 'Start date filter',
      },
      date_to: {
        type: 'string',
        format: 'date',
        description: 'End date filter',
      },
      available_only: {
        type: 'boolean',
        default: false,
        description: 'Only show departures with availability',
      },
      cursor: {
        type: 'string',
        description: 'Pagination cursor',
      },
      limit: {
        type: 'integer',
        minimum: 1,
        maximum: 100,
        default: 20,
        description: 'Results per page',
      },
    },
  },
  CreateHoldRequest: {
    type: 'object',
    required: ['departure_id', 'seats', 'customer_ref'],
    properties: {
      departure_id: {
        type: 'string',
        description: 'Departure to hold seats for',
      },
      seats: {
        type: 'integer',
        minimum: 1,
        maximum: 10,
        description: 'Number of seats to hold',
      },
      customer_ref: {
        type: 'string',
        maxLength: 128,
        description: 'Customer reference',
      },
      ttl_seconds: {
        type: 'integer',
        minimum: 60,
        maximum: 3600,
        default: 600,
        description: 'Hold duration in seconds',
      },
    },
  },
  ConfirmBookingRequest: {
    type: 'object',
    required: ['hold_id'],
    properties: {
      hold_id: {
        type: 'string',
        description: 'Hold to confirm',
      },
    },
  },
  CancelBookingRequest: {
    type: 'object',
    required: ['booking_id'],
    properties: {
      booking_id: {
        type: 'string',
        description: 'Booking to cancel',
      },
    },
  },
  GetBookingRequest: {
    type: 'object',
    required: ['booking_id'],
    properties: {
      booking_id: {
        type: 'string',
        description: 'Booking to retrieve',
      },
    },
  },
  JoinWaitlistRequest: {
    type: 'object',
    required: ['departure_id', 'customer_ref'],
    properties: {
      departure_id: {
        type: 'string',
        description: 'Departure to join waitlist for',
      },
      customer_ref: {
        type: 'string',
        maxLength: 128,
        description: 'Customer reference',
      },
    },
  },
  NotifyWaitlistRequest: {
    type: 'object',
    required: ['departure_id'],
    properties: {
      departure_id: {
        type: 'string',
        description: 'Departure to process waitlist for',
      },
    },
  },
  AdjustInventoryRequest: {
    type: 'object',
    required: ['departure_id', 'delta', 'reason'],
    properties: {
      departure_id: {
        type: 'string',
        description: 'Departure to adjust',
      },
      delta: {
        type: 'integer',
        description: 'Capacity change (positive or negative)',
      },
      reason: {
        type: 'string',
        minLength: 1,
        maxLength: 500,
        description: 'Reason for adjustment',
      },
    },
  },
}

// Example data for each request type
const examples = {
  createTour: {
    name: "Northern Lights Adventure",
    slug: "northern-lights-adventure", 
    description: "Experience the magical Aurora Borealis in Iceland"
  },
  createDeparture: {
    tour_id: "tour_123",
    starts_at: "2024-12-15T09:00:00Z",
    capacity_total: 40,
    price: {
      amount: 29999,
      currency: "USD"
    }
  },
  searchDepartures: {
    tour_id: "tour_123",
    date_from: "2024-12-01",
    date_to: "2024-12-31",
    available_only: true,
    limit: 20
  },
  createHold: {
    departure_id: "dep_123",
    seats: 3,
    customer_ref: "cust_EVG",
    ttl_seconds: 600
  },
  confirmBooking: {
    hold_id: "hold_456"
  },
  cancelBooking: {
    booking_id: "book_789"
  },
  getBooking: {
    booking_id: "book_789"
  },
  joinWaitlist: {
    departure_id: "dep_123",
    customer_ref: "cust_EVG"
  },
  notifyWaitlist: {
    departure_id: "dep_123"
  },
  adjustInventory: {
    departure_id: "dep_123",
    delta: 10,
    reason: "Upgraded to larger bus"
  },
  healthPing: {}
}

// Mapping from operation IDs to schema names
const operationToSchema: Record<string, string | undefined> = {
  createTour: 'CreateTourRequest',
  createDeparture: 'CreateDepartureRequest', 
  searchDepartures: 'SearchDeparturesRequest',
  createHold: 'CreateHoldRequest',
  confirmBooking: 'ConfirmBookingRequest',
  cancelBooking: 'CancelBookingRequest',
  getBooking: 'GetBookingRequest',
  joinWaitlist: 'JoinWaitlistRequest',
  notifyWaitlist: 'NotifyWaitlistRequest',
  adjustInventory: 'AdjustInventoryRequest',
  healthPing: undefined, // No request body
}

// Methods that require idempotency key
const idempotentMethods = new Set([
  'createTour',
  'createDeparture', 
  'createHold',
  'confirmBooking',
  'cancelBooking',
  'joinWaitlist',
  'notifyWaitlist',
  'adjustInventory'
])

export function getMethodSchema(operationId: string): MethodSchema | null {
  // Find the method from the method picker
  const method = (() => {
    // Import the methods dynamically since we can't import from components here
    const methodsByTag = {
      tour: [
        {
          id: 'createTour',
          name: 'Create Tour',
          path: '/v1/tour/create',
          method: 'POST' as const,
          tag: 'tour',
          summary: 'Create a new tour',
          operationId: 'createTour',
          idempotent: true,
        },
      ],
      departure: [
        {
          id: 'createDeparture',
          name: 'Create Departure',
          path: '/v1/departure/create',
          method: 'POST' as const,
          tag: 'departure',
          summary: 'Create a new departure',
          operationId: 'createDeparture',
          idempotent: true,
        },
        {
          id: 'searchDepartures',
          name: 'Search Departures',
          path: '/v1/departure/search',
          method: 'POST' as const,
          tag: 'departure',
          summary: 'Search departures',
          operationId: 'searchDepartures',
        },
      ],
      booking: [
        {
          id: 'createHold',
          name: 'Create Hold',
          path: '/v1/booking/hold',
          method: 'POST' as const,
          tag: 'booking',
          summary: 'Create or refresh a seat hold',
          operationId: 'createHold',
          idempotent: true,
        },
        {
          id: 'confirmBooking',
          name: 'Confirm Booking',
          path: '/v1/booking/confirm',
          method: 'POST' as const,
          tag: 'booking',
          summary: 'Confirm a booking from a hold',
          operationId: 'confirmBooking',
          idempotent: true,
        },
        {
          id: 'cancelBooking',
          name: 'Cancel Booking',
          path: '/v1/booking/cancel',
          method: 'POST' as const,
          tag: 'booking',
          summary: 'Cancel a booking',
          operationId: 'cancelBooking',
          idempotent: true,
        },
        {
          id: 'getBooking',
          name: 'Get Booking',
          path: '/v1/booking/get',
          method: 'POST' as const,
          tag: 'booking',
          summary: 'Get booking details',
          operationId: 'getBooking',
        },
      ],
      waitlist: [
        {
          id: 'joinWaitlist',
          name: 'Join Waitlist',
          path: '/v1/waitlist/join',
          method: 'POST' as const,
          tag: 'waitlist',
          summary: 'Join departure waitlist',
          operationId: 'joinWaitlist',
          idempotent: true,
        },
        {
          id: 'notifyWaitlist',
          name: 'Notify Waitlist',
          path: '/v1/waitlist/notify',
          method: 'POST' as const,
          tag: 'waitlist',
          summary: 'Process waitlist notifications (internal)',
          operationId: 'notifyWaitlist',
          idempotent: true,
          internal: true,
        },
      ],
      inventory: [
        {
          id: 'adjustInventory',
          name: 'Adjust Inventory',
          path: '/v1/inventory/adjust',
          method: 'POST' as const,
          tag: 'inventory',
          summary: 'Adjust departure capacity',
          operationId: 'adjustInventory',
          idempotent: true,
        },
      ],
      health: [
        {
          id: 'healthPing',
          name: 'Health Check',
          path: '/v1/health/ping',
          method: 'POST' as const,
          tag: 'health',
          summary: 'Health check',
          operationId: 'healthPing',
        },
      ],
    }
    
    return Object.values(methodsByTag).flatMap(methods => methods).find(m => m.id === operationId)
  })()

  if (!method) return null

  const schemaName = operationToSchema[operationId]
  const requestSchema = schemaName ? schemas[schemaName as keyof typeof schemas] : undefined
  const requestExample = examples[operationId as keyof typeof examples]

  return {
    method,
    requestSchema: requestSchema as RequestSchema,
    requestExample,
    responses: [], // TODO: Add response schemas
    requiresIdempotencyKey: idempotentMethods.has(operationId),
    requiresAuth: operationId !== 'healthPing', // All methods except health check require auth
  }
}

export function generateFormDefaults(schema: RequestSchema): Record<string, any> {
  const defaults: Record<string, any> = {}
  
  for (const [key, property] of Object.entries(schema.properties)) {
    if (property.default !== undefined) {
      defaults[key] = property.default
    } else if (property.type === 'string') {
      defaults[key] = property.example || ''
    } else if (property.type === 'integer' || property.type === 'number') {
      defaults[key] = property.example || property.minimum || 0
    } else if (property.type === 'boolean') {
      defaults[key] = property.example || false
    } else if (property.type === 'object' && property.properties) {
      defaults[key] = generateFormDefaults({ 
        type: 'object', 
        properties: property.properties, 
        required: property.required || [] 
      })
    }
  }
  
  return defaults
}