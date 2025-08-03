'use client'

import * as React from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Textarea } from "./ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs"
import { Send, Eye, EyeOff, RotateCcw, Save } from "lucide-react"
import { MethodSchema, SchemaProperty, generateFormDefaults } from "@/lib/openapi-parser"
import { generateId } from "@/lib/utils"

interface RequestFormProps {
  methodSchema?: MethodSchema
  onSubmit: (body: any, headers: Record<string, string>) => void
  isLoading?: boolean
}

export function RequestForm({ methodSchema, onSubmit, isLoading }: RequestFormProps) {
  const [formData, setFormData] = React.useState<Record<string, any>>({})
  const [jsonMode, setJsonMode] = React.useState(false)
  const [jsonValue, setJsonValue] = React.useState('')
  const [idempotencyKey, setIdempotencyKey] = React.useState('')
  const [customHeaders, setCustomHeaders] = React.useState<Record<string, string>>({})

  // Reset form when method changes
  React.useEffect(() => {
    if (methodSchema?.requestSchema) {
      const defaults = generateFormDefaults(methodSchema.requestSchema)
      setFormData(defaults)
      setJsonValue(JSON.stringify(methodSchema.requestExample || defaults, null, 2))
    } else {
      setFormData({})
      setJsonValue('{}')
    }
    
    // Generate new idempotency key if required
    if (methodSchema?.requiresIdempotencyKey) {
      setIdempotencyKey(generateId())
    } else {
      setIdempotencyKey('')
    }
  }, [methodSchema])

  const handleFormFieldChange = (path: string, value: any) => {
    setFormData(prev => {
      const newData = { ...prev }
      setNestedValue(newData, path, value)
      return newData
    })
  }

  const handleJsonModeToggle = () => {
    if (jsonMode) {
      // Switching from JSON to form - parse JSON
      try {
        const parsed = JSON.parse(jsonValue)
        setFormData(parsed)
      } catch {
        // Invalid JSON, keep current form data
      }
    } else {
      // Switching from form to JSON - stringify form data
      setJsonValue(JSON.stringify(formData, null, 2))
    }
    setJsonMode(!jsonMode)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const requestBody = jsonMode ? JSON.parse(jsonValue) : formData
    const headers: Record<string, string> = { ...customHeaders }
    
    if (methodSchema?.requiresIdempotencyKey && idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey
    }
    
    onSubmit(requestBody, headers)
  }

  const handleReset = () => {
    if (methodSchema?.requestSchema) {
      const defaults = generateFormDefaults(methodSchema.requestSchema)
      setFormData(defaults)
      setJsonValue(JSON.stringify(methodSchema.requestExample || defaults, null, 2))
    }
    if (methodSchema?.requiresIdempotencyKey) {
      setIdempotencyKey(generateId())
    }
  }

  if (!methodSchema) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Request</CardTitle>
          <CardDescription>Select an API method to build a request</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Request</CardTitle>
            <CardDescription>{methodSchema.method.summary}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleReset}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleJsonModeToggle}
            >
              {jsonMode ? <EyeOff className="h-4 w-4 mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
              {jsonMode ? 'Form' : 'JSON'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Idempotency Key */}
          {methodSchema.requiresIdempotencyKey && (
            <div className="space-y-2">
              <Label htmlFor="idempotency-key" className="flex items-center gap-2">
                Idempotency Key
                <Badge variant="secondary" className="text-xs">Required</Badge>
              </Label>
              <Input
                id="idempotency-key"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                placeholder="Unique key for this request"
                required
              />
            </div>
          )}

          {/* Request Body */}
          {methodSchema.requestSchema && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Request Body</Label>
              
              {jsonMode ? (
                <Textarea
                  value={jsonValue}
                  onChange={(e) => setJsonValue(e.target.value)}
                  className="font-mono text-sm min-h-[200px]"
                  placeholder="Enter JSON request body..."
                />
              ) : (
                <div className="space-y-4 border rounded-lg p-4">
                  {renderFormFields(methodSchema.requestSchema.properties, formData, handleFormFieldChange)}
                </div>
              )}
            </div>
          )}

          {/* Custom Headers */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Custom Headers</Label>
            <Textarea
              value={Object.entries(customHeaders).map(([k, v]) => `${k}: ${v}`).join('\n')}
              onChange={(e) => {
                const headers: Record<string, string> = {}
                e.target.value.split('\n').forEach(line => {
                  const [key, ...valueParts] = line.split(':')
                  if (key && valueParts.length > 0) {
                    headers[key.trim()] = valueParts.join(':').trim()
                  }
                })
                setCustomHeaders(headers)
              }}
              placeholder="Content-Type: application/json&#10;X-Custom-Header: value"
              className="font-mono text-sm"
              rows={3}
            />
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Sending...
              </div>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Request
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

// Helper function to render form fields based on schema
function renderFormFields(
  properties: Record<string, SchemaProperty>,
  formData: Record<string, any>,
  onChange: (path: string, value: any) => void,
  basePath = ''
): React.ReactNode {
  return Object.entries(properties).map(([key, property]) => {
    const path = basePath ? `${basePath}.${key}` : key
    const value = getNestedValue(formData, path)

    if (property.type === 'object' && property.properties) {
      return (
        <div key={key} className="space-y-2">
          <Label className="text-sm font-medium">{key}</Label>
          <div className="border-l-2 border-muted pl-4 space-y-3">
            {renderFormFields(property.properties, formData, onChange, path)}
          </div>
        </div>
      )
    }

    return (
      <div key={key} className="space-y-2">
        <Label htmlFor={path} className="text-sm font-medium flex items-center gap-2">
          {key}
          {property.description && (
            <span className="text-xs text-muted-foreground">({property.description})</span>
          )}
        </Label>
        
        {property.enum ? (
          // Enum - render as select
          <select
            id={path}
            value={value || ''}
            onChange={(e) => onChange(path, e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">Select...</option>
            {property.enum.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        ) : property.type === 'boolean' ? (
          // Boolean - render as checkbox
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id={path}
              checked={value || false}
              onChange={(e) => onChange(path, e.target.checked)}
              className="rounded border-input"
            />
            <Label htmlFor={path} className="text-sm text-muted-foreground">
              {property.description || 'Enable this option'}
            </Label>
          </div>
        ) : (
          // String/number/etc - render as input
          <Input
            id={path}
            type={getInputType(property)}
            value={value || ''}
            onChange={(e) => {
              const val = property.type === 'integer' || property.type === 'number'
                ? parseFloat(e.target.value) || 0
                : e.target.value
              onChange(path, val)
            }}
            placeholder={getPlaceholder(property)}
            min={property.minimum}
            max={property.maximum}
          />
        )}
      </div>
    )
  })
}

// Helper functions
function getInputType(property: SchemaProperty): string {
  if (property.type === 'integer' || property.type === 'number') return 'number'
  if (property.format === 'date-time') return 'datetime-local'
  if (property.format === 'date') return 'date'
  return 'text'
}

function getPlaceholder(property: SchemaProperty): string {
  if (property.example) return String(property.example)
  if (property.format === 'date-time') return '2024-12-15T09:00:00'
  if (property.format === 'date') return '2024-12-15'
  if (property.pattern) return `Pattern: ${property.pattern}`
  return property.description || ''
}

function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj)
}

function setNestedValue(obj: any, path: string, value: any): void {
  const keys = path.split('.')
  const lastKey = keys.pop()!
  const target = keys.reduce((current, key) => {
    if (!(key in current) || typeof current[key] !== 'object') {
      current[key] = {}
    }
    return current[key]
  }, obj)
  target[lastKey] = value
}