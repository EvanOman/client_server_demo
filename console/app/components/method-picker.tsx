'use client'

import * as React from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select"
import { Label } from "./ui/label"
import { Badge } from "./ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Book, Calendar, CreditCard, Users, Activity, Wrench } from "lucide-react"

export interface ApiMethod {
  id: string
  name: string
  path: string
  method: 'POST'
  tag: string
  summary: string
  operationId: string
  idempotent?: boolean
  internal?: boolean
}

const methodsByTag = {
  tour: {
    icon: Book,
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    methods: [
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
  },
  departure: {
    icon: Calendar,
    color: 'bg-green-100 text-green-800 border-green-200',
    methods: [
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
  },
  booking: {
    icon: CreditCard,
    color: 'bg-purple-100 text-purple-800 border-purple-200',
    methods: [
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
  },
  waitlist: {
    icon: Users,
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    methods: [
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
  },
  inventory: {
    icon: Wrench,
    color: 'bg-red-100 text-red-800 border-red-200',
    methods: [
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
  },
  health: {
    icon: Activity,
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    methods: [
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
  },
}

// Flatten all methods for easier access
export const allMethods: ApiMethod[] = Object.values(methodsByTag).flatMap(tag => tag.methods)

interface MethodPickerProps {
  value?: string
  onValueChange: (methodId: string) => void
}

export function MethodPicker({ value, onValueChange }: MethodPickerProps) {
  const selectedMethod = allMethods.find(m => m.id === value)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">API Method</CardTitle>
        <CardDescription>
          Select an API endpoint to test
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="method" className="text-sm font-medium">
            Method
          </Label>
          <Select value={value} onValueChange={onValueChange}>
            <SelectTrigger id="method">
              <SelectValue placeholder="Select an API method...">
                {selectedMethod && (
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {selectedMethod.method}
                    </Badge>
                    <span>{selectedMethod.name}</span>
                  </div>
                )}
              </SelectValue>
            </SelectTrigger>
            <SelectContent className="max-h-80">
              {Object.entries(methodsByTag).map(([tagName, tagInfo]) => {
                const Icon = tagInfo.icon
                return (
                  <div key={tagName}>
                    <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {tagName.charAt(0).toUpperCase() + tagName.slice(1)}
                    </div>
                    {tagInfo.methods.map((method) => (
                      <SelectItem key={method.id} value={method.id}>
                        <div className="flex items-center gap-2 w-full">
                          <Badge variant="outline" className="text-xs">
                            {method.method}
                          </Badge>
                          <span className="flex-1">{method.name}</span>
                          <div className="flex items-center gap-1">
                            {'idempotent' in method && method.idempotent && (
                              <Badge variant="secondary" className="text-xs">
                                Idempotent
                              </Badge>
                            )}
                            {'internal' in method && method.internal && (
                              <Badge variant="destructive" className="text-xs">
                                Internal
                              </Badge>
                            )}
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </div>
                )
              })}
            </SelectContent>
          </Select>
        </div>

        {selectedMethod && (
          <div className="space-y-2 pt-2 border-t">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {selectedMethod.method}
              </Badge>
              <code className="text-sm bg-muted px-2 py-1 rounded">
                {selectedMethod.path}
              </code>
            </div>
            <p className="text-sm text-muted-foreground">
              {selectedMethod.summary}
            </p>
            <div className="flex items-center gap-2">
              {'idempotent' in selectedMethod && selectedMethod.idempotent && (
                <Badge variant="secondary" className="text-xs">
                  Idempotent
                </Badge>
              )}
              {'internal' in selectedMethod && selectedMethod.internal && (
                <Badge variant="destructive" className="text-xs">
                  Internal
                </Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { methodsByTag }