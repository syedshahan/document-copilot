import { ChatShell } from '@/components/chat/ChatShell'

export function ChatListPage() {
  return (
    <ChatShell>
      <div className="grid h-svh place-items-center bg-[radial-gradient(circle_at_center,_white_0,_transparent_55%)] p-8 text-center">
        <div className="max-w-md rounded-3xl border bg-white/80 p-10 shadow-xl shadow-slate-200/50 backdrop-blur">
          <h1 className="text-2xl font-semibold tracking-tight">Your research workspace</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Open a past conversation or create a new one from the sidebar.
          </p>
        </div>
      </div>
    </ChatShell>
  )
}
