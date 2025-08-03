'use client'

import * as React from "react"
import { EnvironmentSwitcher, Environment } from "./components/environment-switcher"
import { AuthManager } from "./components/auth-manager"
import { MethodPicker } from "./components/method-picker"
import { RequestForm } from "./components/request-form"
import { ResponseViewer } from "./components/response-viewer"
import { HistoryDrawer } from "./components/history-drawer"
import { ScenarioManager } from "./components/scenario-manager"
import { Button } from "./components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs"
import { Badge } from "./components/ui/badge"
import { 
  History, 
  Folder, 
  Command,
  Zap,
  Settings,
  Book
} from "lucide-react"
import { ApiClient, ApiRequest, Storage, SavedScenario } from "@/lib/api-client"
import { getMethodSchema } from "@/lib/openapi-parser"

export default function ConsolePage() {
  // State management
  const [environment, setEnvironment] = React.useState<Environment>('local')
  const [bearerToken, setBearerToken] = React.useState('')
  const [selectedMethodId, setSelectedMethodId] = React.useState<string>('')
  const [currentRequest, setCurrentRequest] = React.useState<ApiRequest>()
  const [isLoading, setIsLoading] = React.useState(false)
  
  // UI state
  const [showHistory, setShowHistory] = React.useState(false)
  const [showScenarios, setShowScenarios] = React.useState(false)
  const [showShortcuts, setShowShortcuts] = React.useState(false)

  // API client
  const [apiClient, setApiClient] = React.useState<ApiClient>()

  // Initialize
  React.useEffect(() => {
    // Load saved token
    const savedToken = Storage.getToken(environment)
    setBearerToken(savedToken)
    
    // Initialize API client
    const client = new ApiClient(environment, savedToken)
    setApiClient(client)
  }, [environment])

  // Update API client when config changes
  React.useEffect(() => {
    if (apiClient) {
      apiClient.updateConfig(environment, bearerToken)
    }
  }, [apiClient, environment, bearerToken])

  // Handle token changes
  const handleTokenChange = (token: string) => {
    setBearerToken(token)
    Storage.setToken(environment, token)
  }

  // Handle request submission
  const handleSubmitRequest = async (body: any, headers: Record<string, string>) => {
    if (!apiClient || !selectedMethodId) return

    const methodSchema = getMethodSchema(selectedMethodId)
    if (!methodSchema) return

    setIsLoading(true)
    
    try {
      const request = await apiClient.makeRequest(
        methodSchema.method.path,
        'POST',
        body,
        headers
      )
      
      setCurrentRequest(request)
      Storage.addHistoryItem(request)
    } catch (error) {
      console.error('Request failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Handle scenario operations
  const handleLoadScenario = (scenario: SavedScenario) => {
    setSelectedMethodId(scenario.methodId)
    // The form will update automatically when methodId changes
    setShowScenarios(false)
  }

  const handleSaveScenario = (scenario: Omit<SavedScenario, 'id' | 'createdAt'>) => {
    return Storage.saveScenario(scenario)
  }

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle shortcuts when not typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case 'Enter':
            e.preventDefault()
            // Submit current request
            if (selectedMethodId && !isLoading) {
              const form = document.querySelector('form')
              if (form) {
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))
              }
            }
            break
          case 'h':
            e.preventDefault()
            setShowHistory(true)
            break
          case 's':
            e.preventDefault()
            setShowScenarios(true)
            break
          case '?':
            e.preventDefault()
            setShowShortcuts(true)
            break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [selectedMethodId, isLoading])

  const methodSchema = selectedMethodId ? getMethodSchema(selectedMethodId) || undefined : undefined

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Zap className="h-6 w-6 text-primary" />
                <h1 className="text-xl font-bold">Tour Booking API Console</h1>
              </div>
              {environment && (
                <Badge variant="outline" className="text-xs">
                  {environment}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowHistory(true)}
                className="hidden sm:flex"
              >
                <History className="h-4 w-4 mr-1" />
                History
                <kbd className="kbd ml-2">⌘H</kbd>
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowScenarios(true)}
                className="hidden sm:flex"
              >
                <Folder className="h-4 w-4 mr-1" />
                Scenarios
                <kbd className="kbd ml-2">⌘S</kbd>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowShortcuts(true)}
              >
                <Command className="h-4 w-4 mr-1" />
                <span className="hidden sm:inline">Shortcuts</span>
                <kbd className="kbd ml-2">⌘?</kbd>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="console-grid">
        {/* Sidebar */}
        <aside className="border-r bg-muted/30 p-4 space-y-4 overflow-auto">
          <EnvironmentSwitcher
            value={environment}
            onValueChange={setEnvironment}
          />
          
          <AuthManager
            environment={environment}
            token={bearerToken}
            onTokenChange={handleTokenChange}
          />
          
          <MethodPicker
            value={selectedMethodId}
            onValueChange={setSelectedMethodId}
          />

          {/* Mobile actions */}
          <div className="flex flex-col gap-2 sm:hidden">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowHistory(true)}
            >
              <History className="h-4 w-4 mr-1" />
              History
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowScenarios(true)}
            >
              <Folder className="h-4 w-4 mr-1" />
              Scenarios
            </Button>
          </div>
        </aside>

        {/* Main Area */}
        <main className="console-main">
          <div className="request-response-grid p-4 gap-4">
            <RequestForm
              methodSchema={methodSchema}
              onSubmit={handleSubmitRequest}
              isLoading={isLoading}
            />
            
            <ResponseViewer request={currentRequest} />
          </div>
        </main>
      </div>

      {/* Modals/Drawers */}
      <HistoryDrawer
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        onSelectRequest={setCurrentRequest}
        currentEnvironment={environment}
      />

      <ScenarioManager
        isOpen={showScenarios}
        onClose={() => setShowScenarios(false)}
        onLoadScenario={handleLoadScenario}
        onSaveScenario={handleSaveScenario}
        currentMethodId={selectedMethodId}
        currentBody={undefined} // TODO: Get from form
        currentHeaders={{}}    // TODO: Get from form
      />

      {/* Keyboard Shortcuts Help */}
      {showShortcuts && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background border rounded-lg p-6 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Command className="h-5 w-5" />
                Keyboard Shortcuts
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowShortcuts(false)}
              >
                ×
              </Button>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Send Request</span>
                <kbd className="kbd">⌘Enter</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Show History</span>
                <kbd className="kbd">⌘H</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Show Scenarios</span>
                <kbd className="kbd">⌘S</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Show Shortcuts</span>
                <kbd className="kbd">⌘?</kbd>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}