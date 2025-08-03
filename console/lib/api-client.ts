import { Environment, environments } from '@/app/components/environment-switcher'
import { generateId } from './utils'

export interface ApiRequest {
  id: string
  timestamp: number
  environment: Environment
  method: string
  path: string
  headers: Record<string, string>
  body?: any
  duration?: number
  response?: ApiResponse
  error?: string
}

export interface ApiResponse {
  status: number
  statusText: string
  headers: Record<string, string>
  body?: any
  duration: number
  traceId?: string
}

export class ApiClient {
  private baseUrl: string
  private bearerToken?: string

  constructor(environment: Environment, bearerToken?: string) {
    this.baseUrl = environments[environment].url
    this.bearerToken = bearerToken
  }

  updateConfig(environment: Environment, bearerToken?: string) {
    this.baseUrl = environments[environment].url
    this.bearerToken = bearerToken
  }

  async makeRequest(
    path: string,
    method: 'POST' = 'POST',
    body?: any,
    additionalHeaders?: Record<string, string>
  ): Promise<ApiRequest> {
    const requestId = generateId()
    const timestamp = Date.now()
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...additionalHeaders,
    }

    if (this.bearerToken && path !== '/v1/health/ping') {
      headers.Authorization = `Bearer ${this.bearerToken}`
    }

    const request: ApiRequest = {
      id: requestId,
      timestamp,
      environment: this.getEnvironmentFromUrl(),
      method,
      path,
      headers,
      body,
    }

    const startTime = performance.now()

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      })

      const endTime = performance.now()
      const duration = Math.round(endTime - startTime)

      const responseHeaders: Record<string, string> = {}
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value
      })

      let responseBody: any
      const contentType = response.headers.get('content-type')
      
      if (contentType?.includes('application/json') || contentType?.includes('application/problem+json')) {
        try {
          responseBody = await response.json()
        } catch {
          responseBody = null
        }
      } else {
        responseBody = await response.text()
      }

      const apiResponse: ApiResponse = {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
        body: responseBody,
        duration,
        traceId: responseHeaders['x-trace-id'] || responseHeaders['trace-id'],
      }

      request.response = apiResponse
      request.duration = duration

      return request

    } catch (error) {
      const endTime = performance.now()
      const duration = Math.round(endTime - startTime)
      
      request.error = error instanceof Error ? error.message : 'Unknown error'
      request.duration = duration

      return request
    }
  }

  private getEnvironmentFromUrl(): Environment {
    if (this.baseUrl.includes('localhost')) return 'local'
    if (this.baseUrl.includes('staging')) return 'staging'
    return 'local' // fallback
  }
}

// Storage helpers
const STORAGE_KEY = 'tour-booking-console'

interface StorageData {
  tokens: Record<Environment, string>
  history: ApiRequest[]
  scenarios: SavedScenario[]
}

export interface SavedScenario {
  id: string
  name: string
  description?: string
  methodId: string
  body: any
  headers: Record<string, string>
  createdAt: number
}

export class Storage {
  private static getData(): StorageData {
    if (typeof window === 'undefined') {
      return { tokens: {} as Record<Environment, string>, history: [], scenarios: [] }
    }

    try {
      const data = localStorage.getItem(STORAGE_KEY)
      if (!data) {
        return { tokens: {} as Record<Environment, string>, history: [], scenarios: [] }
      }
      return JSON.parse(data)
    } catch {
      return { tokens: {} as Record<Environment, string>, history: [], scenarios: [] }
    }
  }

  private static setData(data: StorageData): void {
    if (typeof window === 'undefined') return

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.warn('Failed to save to localStorage:', error)
    }
  }

  static getToken(environment: Environment): string {
    return this.getData().tokens[environment] || ''
  }

  static setToken(environment: Environment, token: string): void {
    const data = this.getData()
    data.tokens[environment] = token
    this.setData(data)
  }

  static getHistory(): ApiRequest[] {
    return this.getData().history
  }

  static addHistoryItem(request: ApiRequest): void {
    const data = this.getData()
    data.history.unshift(request) // Add to beginning
    
    // Keep only last 100 requests
    if (data.history.length > 100) {
      data.history = data.history.slice(0, 100)
    }
    
    this.setData(data)
  }

  static clearHistory(): void {
    const data = this.getData()
    data.history = []
    this.setData(data)
  }

  static getScenarios(): SavedScenario[] {
    return this.getData().scenarios
  }

  static saveScenario(scenario: Omit<SavedScenario, 'id' | 'createdAt'>): SavedScenario {
    const data = this.getData()
    const newScenario: SavedScenario = {
      ...scenario,
      id: generateId(),
      createdAt: Date.now(),
    }
    
    data.scenarios.push(newScenario)
    this.setData(data)
    
    return newScenario
  }

  static deleteScenario(id: string): void {
    const data = this.getData()
    data.scenarios = data.scenarios.filter(s => s.id !== id)
    this.setData(data)
  }

  static exportData(): string {
    return JSON.stringify(this.getData(), null, 2)
  }

  static importData(jsonData: string): boolean {
    try {
      const data = JSON.parse(jsonData)
      // Basic validation
      if (typeof data === 'object' && data !== null) {
        this.setData(data)
        return true
      }
      return false
    } catch {
      return false
    }
  }
}