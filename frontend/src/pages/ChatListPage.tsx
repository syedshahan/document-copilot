import { ChatShell } from '@/components/chat/ChatShell'

export function ChatListPage() {
  return (
    <ChatShell>
      <div className="grid h-svh place-items-center p-8 text-center">
        <div>
          <h1 className="m-0 text-2xl font-semibold tracking-normal">Choose a conversation</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Open a past conversation or create a new one from the sidebar.
          </p>
        </div>
      </div>
    </ChatShell>
  )
}
