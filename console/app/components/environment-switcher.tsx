'use client'

import * as React from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select"
import { Label } from "./ui/label"
import { Globe, Server } from "lucide-react"

export type Environment = 'local' | 'staging'

interface EnvironmentConfig {
  name: string
  url: string
  icon: React.ComponentType<{ className?: string }>
}

const environments: Record<Environment, EnvironmentConfig> = {
  local: {
    name: 'Local',
    url: 'http://localhost:8000',
    icon: Server,
  },
  staging: {
    name: 'Staging',
    url: 'https://api.staging.example.com',
    icon: Globe,
  },
}

interface EnvironmentSwitcherProps {
  value: Environment
  onValueChange: (value: Environment) => void
}

export function EnvironmentSwitcher({ value, onValueChange }: EnvironmentSwitcherProps) {
  const currentEnv = environments[value]
  const Icon = currentEnv.icon

  return (
    <div className="space-y-2">
      <Label htmlFor="environment" className="text-sm font-medium">
        Environment
      </Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id="environment" className="w-full">
          <SelectValue>
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              <span>{currentEnv.name}</span>
              <span className="text-muted-foreground text-xs">({currentEnv.url})</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {Object.entries(environments).map(([key, env]) => {
            const EnvIcon = env.icon
            return (
              <SelectItem key={key} value={key}>
                <div className="flex items-center gap-2">
                  <EnvIcon className="h-4 w-4" />
                  <span>{env.name}</span>
                  <span className="text-muted-foreground text-xs">({env.url})</span>
                </div>
              </SelectItem>
            )
          })}
        </SelectContent>
      </Select>
    </div>
  )
}

export { environments, type EnvironmentConfig }