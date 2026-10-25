import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/use-auth'

export function PublicOnlyRoute() {
  const { session, isLoading } = useAuth()

  if (isLoading) {
    return (
      <main className="grid min-h-svh place-items-center bg-muted/40">
        <p className="text-sm text-muted-foreground">Checking your session…</p>
      </main>
    )
  }
  return session ? <Navigate to="/workspace" replace /> : <Outlet />
}
