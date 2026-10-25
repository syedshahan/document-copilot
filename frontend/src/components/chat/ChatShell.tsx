import { useEffect, useState, type ReactNode } from 'react'
import { LogOut, MessageSquare, Plus } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { chats, type ChatThread } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type ChatShellProps = {
  children: ReactNode
}

export function ChatShell({ children }: ChatShellProps) {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void chats
      .listThreads({ signal: controller.signal })
      .then(setThreads)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(errorMessage(requestError))
        }
      })
    return () => controller.abort()
  }, [])

  async function handleNewThread() {
    setIsCreating(true)
    setError(null)
    try {
      const thread = await chats.createThread()
      setThreads((current) => [thread, ...current])
      navigate(`/chats/${thread.id}`)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <main className="flex min-h-svh bg-background text-foreground">
      <aside className="flex w-72 shrink-0 flex-col border-r bg-sidebar p-3">
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquare className="size-4" />
          </div>
          <div>
            <p className="font-semibold text-sidebar-foreground">Document Copilot</p>
            <p className="text-xs text-muted-foreground">Research workspace</p>
          </div>
        </div>

        <Button className="mt-2 justify-start" onClick={handleNewThread} disabled={isCreating}>
          <Plus className="size-4" />
          {isCreating ? 'Creating…' : 'New conversation'}
        </Button>

        <nav className="mt-5 flex-1 space-y-1 overflow-y-auto" aria-label="Conversations">
          <p className="px-2 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Conversations
          </p>
          {threads.map((thread) => (
            <NavLink
              key={thread.id}
              to={`/chats/${thread.id}`}
              className={({ isActive }) =>
                `block truncate rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                    : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                }`
              }
            >
              {thread.title}
            </NavLink>
          ))}
          {!threads.length && !error ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">No conversations yet.</p>
          ) : null}
          {error ? <p className="px-2 py-3 text-sm text-destructive">{error}</p> : null}
        </nav>

        <Button variant="ghost" className="justify-start" onClick={() => void supabase.auth.signOut()}>
          <LogOut className="size-4" />
          Sign out
        </Button>
      </aside>
      <section className="min-w-0 flex-1">{children}</section>
    </main>
  )
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.'
}
