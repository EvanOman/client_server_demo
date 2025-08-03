'use client'

import * as React from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Textarea } from "./ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs"
import { 
  Save, 
  Folder, 
  Play,
  Trash2,
  Download,
  Upload,
  FileText,
  X
} from "lucide-react"
import { SavedScenario, Storage } from "@/lib/api-client"
import { allMethods } from "./method-picker"

interface ScenarioManagerProps {
  isOpen: boolean
  onClose: () => void
  onLoadScenario: (scenario: SavedScenario) => void
  onSaveScenario: (scenario: Omit<SavedScenario, 'id' | 'createdAt'>) => SavedScenario
  currentMethodId?: string
  currentBody?: any
  currentHeaders?: Record<string, string>
}

export function ScenarioManager({
  isOpen,
  onClose,
  onLoadScenario,
  onSaveScenario,
  currentMethodId,
  currentBody,
  currentHeaders = {}
}: ScenarioManagerProps) {
  const [scenarios, setScenarios] = React.useState<SavedScenario[]>([])
  const [activeTab, setActiveTab] = React.useState<'saved' | 'save-new'>('saved')
  const [newScenario, setNewScenario] = React.useState({
    name: '',
    description: '',
  })

  React.useEffect(() => {
    if (isOpen) {
      setScenarios(Storage.getScenarios())
    }
  }, [isOpen])

  const handleSaveNew = () => {
    if (!newScenario.name.trim() || !currentMethodId) return

    const scenario = {
      name: newScenario.name.trim(),
      description: newScenario.description.trim() || undefined,
      methodId: currentMethodId,
      body: currentBody || {},
      headers: currentHeaders,
    }

    const saved = onSaveScenario(scenario)
    setScenarios(prev => [...prev, saved])
    setNewScenario({ name: '', description: '' })
    setActiveTab('saved')
  }

  const handleDeleteScenario = (id: string) => {
    Storage.deleteScenario(id)
    setScenarios(prev => prev.filter(s => s.id !== id))
  }

  const handleExportScenarios = () => {
    const dataStr = JSON.stringify(scenarios, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    
    const exportFileDefaultName = `api-scenarios-${new Date().toISOString().split('T')[0]}.json`
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const handleImportScenarios = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedScenarios = JSON.parse(e.target?.result as string)
        if (Array.isArray(importedScenarios)) {
          // Add imported scenarios to storage
          importedScenarios.forEach(scenario => {
            if (scenario.name && scenario.methodId) {
              Storage.saveScenario(scenario)
            }
          })
          setScenarios(Storage.getScenarios())
        }
      } catch (error) {
        console.error('Failed to import scenarios:', error)
      }
    }
    reader.readAsText(file)
    
    // Reset input
    event.target.value = ''
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-background border rounded-lg w-full max-w-4xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Folder className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Saved Scenarios</h2>
            <Badge variant="outline">{scenarios.length}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExportScenarios}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            <label className="cursor-pointer">
              <Button variant="outline" size="sm" asChild>
                <span>
                  <Upload className="h-4 w-4 mr-1" />
                  Import
                </span>
              </Button>
              <input
                type="file"
                accept=".json"
                onChange={handleImportScenarios}
                className="hidden"
              />
            </label>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="h-full flex flex-col">
            <TabsList className="mx-4 mt-4">
              <TabsTrigger value="saved">Saved Scenarios</TabsTrigger>
              <TabsTrigger value="save-new" disabled={!currentMethodId}>
                Save Current
              </TabsTrigger>
            </TabsList>

            <TabsContent value="saved" className="flex-1 overflow-auto p-4">
              {scenarios.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No saved scenarios yet</p>
                  <p className="text-sm">Save your current request to get started</p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {scenarios.map((scenario) => (
                    <ScenarioCard
                      key={scenario.id}
                      scenario={scenario}
                      onLoad={() => onLoadScenario(scenario)}
                      onDelete={() => handleDeleteScenario(scenario.id)}
                    />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="save-new" className="flex-1 overflow-auto p-4">
              <div className="max-w-md mx-auto space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Save Current Request</CardTitle>
                    <CardDescription>
                      Save the current request as a reusable scenario
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="scenario-name">Name *</Label>
                      <Input
                        id="scenario-name"
                        placeholder="e.g., Create demo tour"
                        value={newScenario.name}
                        onChange={(e) => setNewScenario(prev => ({ ...prev, name: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="scenario-description">Description</Label>
                      <Textarea
                        id="scenario-description"
                        placeholder="Optional description..."
                        value={newScenario.description}
                        onChange={(e) => setNewScenario(prev => ({ ...prev, description: e.target.value }))}
                        rows={3}
                      />
                    </div>

                    {currentMethodId && (
                      <div className="space-y-2">
                        <Label>Current Method</Label>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">POST</Badge>
                          <span className="text-sm">
                            {allMethods.find(m => m.id === currentMethodId)?.name}
                          </span>
                        </div>
                      </div>
                    )}

                    <Button 
                      onClick={handleSaveNew}
                      disabled={!newScenario.name.trim() || !currentMethodId}
                      className="w-full"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save Scenario
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

interface ScenarioCardProps {
  scenario: SavedScenario
  onLoad: () => void
  onDelete: () => void
}

function ScenarioCard({ scenario, onLoad, onDelete }: ScenarioCardProps) {
  const method = allMethods.find(m => m.id === scenario.methodId)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{scenario.name}</CardTitle>
            {scenario.description && (
              <CardDescription className="mt-1">
                {scenario.description}
              </CardDescription>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">POST</Badge>
          <span className="text-sm text-muted-foreground">
            {method?.name || scenario.methodId}
          </span>
        </div>

        <div className="text-xs text-muted-foreground">
          Created {new Date(scenario.createdAt).toLocaleDateString()}
        </div>

        <Button onClick={onLoad} size="sm" className="w-full">
          <Play className="h-4 w-4 mr-2" />
          Load Scenario
        </Button>
      </CardContent>
    </Card>
  )
}