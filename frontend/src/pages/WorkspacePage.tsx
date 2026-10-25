import { useEffect, useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { api } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type CurrentUser = {
  id: string
  email: string | null
}

export function WorkspacePage() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSigningOut, setIsSigningOut] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    void api
      .get<CurrentUser>('/auth/me', { signal: controller.signal })
      .then(setUser)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Could not verify your session with the backend.',
          )
        }
      })

    return () => controller.abort()
  }, [])

  async function handleSignOut() {
    setIsSigningOut(true)
    const { error: signOutError } = await supabase.auth.signOut()
    if (signOutError) {
      setError(signOutError.message)
      setIsSigningOut(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 px-4 py-10">
      <Card className="w-full max-w-xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Document Copilot</CardTitle>
          <CardDescription>Protected workspace</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <AlertDescription>
                {user
                  ? `Authenticated with FastAPI as ${user.email ?? user.id}.`
                  : 'Verifying your Supabase token with FastAPI…'}
              </AlertDescription>
            </Alert>
          )}

          <p className="text-sm text-muted-foreground">
            Authentication is connected. Chat functionality is the next phase.
          </p>

          <Button
            variant="outline"
            onClick={handleSignOut}
            disabled={isSigningOut}
          >
            {isSigningOut ? 'Signing out…' : 'Sign out'}
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
