'use client'

import * as React from "react"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Button } from "./ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Eye, EyeOff, Key, Trash2 } from "lucide-react"
import { Environment } from "./environment-switcher"

interface AuthManagerProps {
  environment: Environment
  token: string
  onTokenChange: (token: string) => void
}

export function AuthManager({ environment, token, onTokenChange }: AuthManagerProps) {
  const [showToken, setShowToken] = React.useState(false)
  const [tempToken, setTempToken] = React.useState(token)

  React.useEffect(() => {
    setTempToken(token)
  }, [token])

  const handleSave = () => {
    onTokenChange(tempToken)
  }

  const handleClear = () => {
    setTempToken('')
    onTokenChange('')
  }

  const isChanged = tempToken !== token

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Key className="h-4 w-4" />
          Authentication
        </CardTitle>
        <CardDescription>
          Bearer token for <span className="font-mono">{environment}</span> environment
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="token" className="text-sm font-medium">
            Bearer Token
          </Label>
          <div className="relative">
            <Input
              id="token"
              type={showToken ? "text" : "password"}
              placeholder="Enter your bearer token..."
              value={tempToken}
              onChange={(e) => setTempToken(e.target.value)}
              className="pr-20"
            />
            <div className="absolute right-1 top-1/2 -translate-y-1/2 flex gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setShowToken(!showToken)}
              >
                {showToken ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
              {tempToken && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={handleClear}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
        
        {isChanged && (
          <div className="flex gap-2">
            <Button onClick={handleSave} size="sm" className="flex-1">
              Save Token
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setTempToken(token)}
            >
              Cancel
            </Button>
          </div>
        )}
        
        {token && (
          <div className="text-xs text-muted-foreground">
            Token: {showToken ? token : `${'*'.repeat(Math.min(token.length, 20))}${token.length > 20 ? '...' : ''}`}
          </div>
        )}
      </CardContent>
    </Card>
  )
}