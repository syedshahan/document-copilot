import { useEffect, useState, type ReactNode } from 'react'
import { FileStack, LogOut, MessageSquareText, Plus, Sparkles } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { chats, type ChatThread } from '@/lib/api'
import { supabase } from '@/lib/supabase'

export function ChatShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void chats.listThreads({ signal: controller.signal }).then(setThreads).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(requestError))
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
      <aside className="flex w-72 shrink-0 flex-col border-r border-sidebar-border bg-sidebar/95 p-4 max-md:w-20 max-md:p-3">
        <div className="flex items-center gap-3 px-1 py-2">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20"><FileStack className="size-5" /></div>
          <div className="min-w-0 max-md:hidden">
            <p className="truncate font-semibold tracking-tight text-sidebar-foreground">Document Copilot</p>
            <p className="flex items-center gap-1 text-xs text-muted-foreground"><Sparkles className="size-3" /> SEC research workspace</p>
          </div>
        </div>

        <Button className="mt-4 h-10 justify-start rounded-xl shadow-sm max-md:size-11 max-md:px-0" onClick={handleNewThread} disabled={isCreating} aria-label="New conversation">
          <Plus className="size-4" /><span className="max-md:hidden">{isCreating ? 'Creating…' : 'New conversation'}</span>
        </Button>

        <nav className="mt-7 flex-1 space-y-1.5 overflow-y-auto" aria-label="Conversations">
          <p className="px-2 pb-1 text-[0.6875rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground max-md:hidden">Conversations</p>
          {threads.map((thread) => (
            <NavLink key={thread.id} to={`/chats/${thread.id}`} title={thread.title} className={({ isActive }) =>
              `group flex items-center gap-2.5 truncate rounded-xl px-3 py-2.5 text-sm transition-all max-md:justify-center max-md:px-0 ${isActive ? 'bg-white font-medium text-sidebar-accent-foreground shadow-sm ring-1 ring-black/5' : 'text-muted-foreground hover:bg-white/70 hover:text-sidebar-foreground'}`
            }>
              <MessageSquareText className="size-4 shrink-0 opacity-70" /><span className="truncate max-md:hidden">{thread.title}</span>
            </NavLink>
          ))}
          {!threads.length && !error ? <p className="px-2 py-3 text-sm text-muted-foreground max-md:hidden">No conversations yet.</p> : null}
          {error ? <p className="px-2 py-3 text-sm text-destructive max-md:hidden">{error}</p> : null}
        </nav>

        <Button variant="ghost" className="h-10 justify-start rounded-xl text-muted-foreground max-md:size-11 max-md:px-0" onClick={() => void supabase.auth.signOut()} aria-label="Sign out">
          <LogOut className="size-4" /><span className="max-md:hidden">Sign out</span>
        </Button>
      </aside>
      <section className="min-w-0 flex-1">{children}</section>
    </main>
  )
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.'
}
