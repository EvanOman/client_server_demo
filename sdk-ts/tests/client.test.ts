import { describe, it, expect } from 'vitest';
import { Client, createClient, ApiError, generateIdempotencyKey } from '../src/index.js';

describe('Client SDK', () => {
  it('should create a client instance', () => {
    const client = new Client({
      baseUrl: 'https://api.example.com',
      token: 'test-token'
    });

    expect(client).toBeInstanceOf(Client);
  });

  it('should create a client using factory function', () => {
    const client = createClient({
      baseUrl: 'https://api.example.com',
      token: 'test-token'
    });

    expect(client).toBeInstanceOf(Client);
  });

  it('should generate idempotency keys', () => {
    const key1 = generateIdempotencyKey();
    const key2 = generateIdempotencyKey();

    expect(typeof key1).toBe('string');
    expect(typeof key2).toBe('string');
    expect(key1).not.toBe(key2);
    expect(key1.length).toBeGreaterThan(0);
  });

  it('should throw ClientError for missing required options', () => {
    expect(() => {
      new Client({
        baseUrl: '',
        token: ''
      });
    }).toThrow();
  });

  it('should export ApiError class', () => {
    const problem = {
      title: 'Test Error',
      status: 400
    };
    
    const error = new ApiError(problem);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe('Test Error');
    expect(error.status).toBe(400);
  });
});