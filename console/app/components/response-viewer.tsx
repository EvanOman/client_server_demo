'use client'

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs"
import { Button } from "./ui/button"
import { Copy, ExternalLink, Clock, Zap } from "lucide-react"
import { ApiRequest } from "@/lib/api-client"
import { formatDuration } from "@/lib/utils"

interface ResponseViewerProps {
  request?: ApiRequest
}

export function ResponseViewer({ request }: ResponseViewerProps) {
  const [copiedSection, setCopiedSection] = React.useState<string | null>(null)

  const copyToClipboard = async (text: string, section: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedSection(section)
      setTimeout(() => setCopiedSection(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  if (!request) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Response</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            Send a request to see the response
          </div>
        </CardContent>
      </Card>
    )
  }

  const response = request.response
  const hasError = !response || request.error

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Response</CardTitle>
          <div className="flex items-center gap-2">
            {request.duration && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDuration(request.duration)}
              </Badge>
            )}
            {response?.traceId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // TODO: Link to trace viewer if available
                  console.log('Trace ID:', response.traceId)
                }}
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                Trace
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {hasError ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="destructive">Error</Badge>
              <span className="text-sm text-muted-foreground">
                Request failed
              </span>
            </div>
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <code className="text-sm text-destructive">
                {request.error || 'Unknown error occurred'}
              </code>
            </div>
          </div>
        ) : (
          <Tabs defaultValue="body" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="body">Body</TabsTrigger>
              <TabsTrigger value="headers">Headers</TabsTrigger>
              <TabsTrigger value="raw">Raw</TabsTrigger>
            </TabsList>

            <TabsContent value="body" className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge 
                    variant={getStatusVariant(response!.status)}
                    className="flex items-center gap-1"
                  >
                    <Zap className="h-3 w-3" />
                    {response!.status} {response!.statusText}
                  </Badge>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(
                    typeof response!.body === 'string' 
                      ? response!.body 
                      : JSON.stringify(response!.body, null, 2),
                    'body'
                  )}
                >
                  <Copy className="h-4 w-4 mr-1" />
                  {copiedSection === 'body' ? 'Copied!' : 'Copy'}
                </Button>
              </div>

              <div className="bg-muted rounded-lg p-4 overflow-auto max-h-96">
                <pre className="text-sm code-editor">
                  {typeof response!.body === 'string' 
                    ? response!.body 
                    : JSON.stringify(response!.body, null, 2)
                  }
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="headers" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Response Headers</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(
                    Object.entries(response!.headers)
                      .map(([key, value]) => `${key}: ${value}`)
                      .join('\n'),
                    'headers'
                  )}
                >
                  <Copy className="h-4 w-4 mr-1" />
                  {copiedSection === 'headers' ? 'Copied!' : 'Copy'}
                </Button>
              </div>

              <div className="bg-muted rounded-lg p-4 overflow-auto max-h-96">
                <div className="space-y-1">
                  {Object.entries(response!.headers).map(([key, value]) => (
                    <div key={key} className="text-sm code-editor">
                      <span className="text-muted-foreground">{key}:</span>{' '}
                      <span>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="raw" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Raw Response</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const rawResponse = [
                      `HTTP/1.1 ${response!.status} ${response!.statusText}`,
                      ...Object.entries(response!.headers).map(([key, value]) => `${key}: ${value}`),
                      '',
                      typeof response!.body === 'string' 
                        ? response!.body 
                        : JSON.stringify(response!.body, null, 2)
                    ].join('\n')
                    copyToClipboard(rawResponse, 'raw')
                  }}
                >
                  <Copy className="h-4 w-4 mr-1" />
                  {copiedSection === 'raw' ? 'Copied!' : 'Copy'}
                </Button>
              </div>

              <div className="bg-muted rounded-lg p-4 overflow-auto max-h-96">
                <pre className="text-sm code-editor">
                  {`HTTP/1.1 ${response!.status} ${response!.statusText}`}
                  {'\n'}
                  {Object.entries(response!.headers).map(([key, value]) => `${key}: ${value}`).join('\n')}
                  {'\n\n'}
                  {typeof response!.body === 'string' 
                    ? response!.body 
                    : JSON.stringify(response!.body, null, 2)
                  }
                </pre>
              </div>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}

function getStatusVariant(status: number): "default" | "secondary" | "destructive" | "outline" {
  if (status >= 200 && status < 300) return "default"
  if (status >= 300 && status < 400) return "secondary"
  if (status >= 400) return "destructive"
  return "outline"
}