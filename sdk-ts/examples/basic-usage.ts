/**
 * Basic usage example for the Tour Booking SDK
 * 
 * This example demonstrates:
 * - Creating a client
 * - Creating tours and departures
 * - Searching departures  
 * - Booking flow (hold -> confirm)
 * - Error handling
 */

import { Client, ApiError, isApiError } from '../src/index.js';

async function main() {
  // Create a client instance
  const client = new Client({
    baseUrl: 'http://localhost:8000',
    token: 'your-bearer-token-here',
    debug: true, // Enable request/response logging
    timeoutMs: 10000, // 10 second timeout
  });

  try {
    console.log('🌟 Creating a new tour...');
    
    // Create a tour
    const tourResponse = await client.createTour({
      name: 'Northern Lights Adventure',
      slug: 'northern-lights-adventure',
      description: 'Experience the magical Aurora Borealis in Iceland'
    });
    
    console.log('✅ Tour created:', tourResponse.data);
    console.log('📊 Request took:', tourResponse.duration, 'ms');
    console.log('🔍 Trace ID:', tourResponse.traceId);

    console.log('\n🚌 Creating a departure...');
    
    // Create a departure for the tour
    const departureResponse = await client.createDeparture({
      tour_id: tourResponse.data.id,
      starts_at: '2024-12-15T09:00:00Z',
      capacity_total: 40,
      price: {
        amount: 29999, // $299.99 in cents
        currency: 'USD'
      }
    });
    
    console.log('✅ Departure created:', departureResponse.data);

    console.log('\n🔍 Searching departures...');
    
    // Search for available departures
    const searchResponse = await client.searchDepartures({
      tour_id: tourResponse.data.id,
      available_only: true,
      limit: 10
    });
    
    console.log('✅ Found departures:', searchResponse.data.items.length);

    if (searchResponse.data.items.length > 0) {
      const departure = searchResponse.data.items[0];
      
      console.log('\n🎫 Creating a hold...');
      
      // Hold seats
      const holdResponse = await client.createHold({
        departure_id: departure.id,
        seats: 2,
        customer_ref: 'customer-123',
        ttl_seconds: 600 // 10 minutes
      });
      
      console.log('✅ Hold created:', holdResponse.data);
      console.log('⏰ Expires at:', holdResponse.data.expires_at);

      console.log('\n✅ Confirming booking...');
      
      // Confirm the booking
      const bookingResponse = await client.confirmBooking({
        hold_id: holdResponse.data.id
      });
      
      console.log('✅ Booking confirmed:', bookingResponse.data);
      console.log('🎟️  Booking code:', bookingResponse.data.code);

      console.log('\n📋 Getting booking details...');
      
      // Get booking details
      const getBookingResponse = await client.getBooking({
        booking_id: bookingResponse.data.id
      });
      
      console.log('✅ Booking details:', getBookingResponse.data);
    }

    console.log('\n🏥 Health check...');
    
    // Health check (no auth required)
    const healthResponse = await client.healthPing();
    console.log('✅ Service healthy:', healthResponse.data);

  } catch (error) {
    if (isApiError(error)) {
      console.error('❌ API Error:', {
        status: error.status,
        code: error.code,
        title: error.message,
        detail: error.detailMessage,
        traceId: error.traceId,
        retryable: error.retryable
      });
      
      // Handle specific error codes
      if (error.code === 'FULL') {
        console.log('💡 Departure is full, try joining the waitlist');
        
        // Example: Join waitlist if capacity is full
        // await client.joinWaitlist({
        //   departure_id: 'dep_123',
        //   customer_ref: 'customer-123'
        // });
      }
    } else {
      console.error('❌ Unexpected error:', error);
    }
  }
}

// Run the example if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { main };