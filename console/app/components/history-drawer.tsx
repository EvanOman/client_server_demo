'use client'

import * as React from "react"
import { Button } from "./ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs"
import { 
  History, 
  Clock, 
  Trash2, 
  Download, 
  Upload,
  Search,
  Filter,
  X
} from "lucide-react"
import { Input } from "./ui/input"
import { ApiRequest, Storage } from "@/lib/api-client"
import { formatDuration } from "@/lib/utils"
import { Environment } from "./environment-switcher"

interface HistoryDrawerProps {
  isOpen: boolean
  onClose: () => void
  onSelectRequest: (request: ApiRequest) => void
  currentEnvironment: Environment
}

export function HistoryDrawer({ 
  isOpen, 
  onClose, 
  onSelectRequest,
  currentEnvironment 
}: HistoryDrawerProps) {
  const [history, setHistory] = React.useState<ApiRequest[]>([])
  const [searchQuery, setSearchQuery] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')

  React.useEffect(() => {
    if (isOpen) {
      setHistory(Storage.getHistory())
    }
  }, [isOpen])

  const filteredHistory = React.useMemo(() => {
    return history.filter(request => {
      // Environment filter
      if (request.environment !== currentEnvironment) return false
      
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesPath = request.path.toLowerCase().includes(query)
        const matchesMethod = request.method.toLowerCase().includes(query)
        const matchesStatus = request.response?.status.toString().includes(query)
        if (!matchesPath && !matchesMethod && !matchesStatus) return false
      }
      
      // Status filter
      if (statusFilter !== 'all') {
        if (statusFilter === 'success' && (!request.response || request.response.status >= 400)) return false
        if (statusFilter === 'error' && (request.response && request.response.status < 400)) return false
      }
      
      return true
    })
  }, [history, searchQuery, statusFilter, currentEnvironment])

  const handleClearHistory = () => {
    Storage.clearHistory()
    setHistory([])
  }

  const handleExportHistory = () => {
    const dataStr = JSON.stringify(filteredHistory, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    
    const exportFileDefaultName = `api-history-${new Date().toISOString().split('T')[0]}.json`
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex">
      <div className="w-full max-w-2xl bg-background border-l ml-auto flex flex-col h-full">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <History className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Request History</h2>
            <Badge variant="outline">{filteredHistory.length}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExportHistory}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            <Button variant="outline" size="sm" onClick={handleClearHistory}>
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="p-4 border-b space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search requests..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-md bg-background text-sm"
            >
              <option value="all">All Status</option>
              <option value="success">Success (2xx-3xx)</option>
              <option value="error">Error (4xx-5xx)</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {filteredHistory.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              {history.length === 0 
                ? "No requests in history" 
                : "No requests match your filters"
              }
            </div>
          ) : (
            <div className="space-y-3">
              {filteredHistory.map((request) => (
                <HistoryItem
                  key={request.id}
                  request={request}
                  onClick={() => onSelectRequest(request)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface HistoryItemProps {
  request: ApiRequest
  onClick: () => void
}

function HistoryItem({ request, onClick }: HistoryItemProps) {
  const getStatusBadge = () => {
    if (request.error) {
      return <Badge variant="destructive">Error</Badge>
    }
    if (!request.response) {
      return <Badge variant="outline">Pending</Badge>
    }
    
    const status = request.response.status
    if (status >= 200 && status < 300) {
      return <Badge variant="default">{status}</Badge>
    } else if (status >= 400) {
      return <Badge variant="destructive">{status}</Badge>
    } else {
      return <Badge variant="secondary">{status}</Badge>
    }
  }

  return (
    <Card 
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {request.method}
            </Badge>
            {getStatusBadge()}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {request.duration && (
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDuration(request.duration)}
              </div>
            )}
            <span>
              {new Date(request.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
        
        <div className="text-sm font-mono text-muted-foreground mb-2">
          {request.path}
        </div>
        
        {request.error && (
          <div className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">
            {request.error}
          </div>
        )}
        
        {request.response?.traceId && (
          <div className="text-xs text-muted-foreground">
            Trace: {request.response.traceId}
          </div>
        )}
      </CardContent>
    </Card>
  )
}