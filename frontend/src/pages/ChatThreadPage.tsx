import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { ChatConversation } from '@/components/chat/ChatConversation'
import { ChatShell } from '@/components/chat/ChatShell'
import { isAnswerStatusData, isCitationData, type DocumentUIMessage } from '@/components/chat/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { chats, type StoredChatMessage } from '@/lib/api'

export function ChatThreadPage() {
  const { threadId } = useParams<{ threadId: string }>()
  if (!threadId) return null

  return (
    <ChatShell>
      <Thread threadId={threadId} key={threadId} />
    </ChatShell>
  )
}

function Thread({ threadId }: { threadId: string }) {
  const [messages, setMessages] = useState<DocumentUIMessage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void chats
      .listMessages(threadId, { signal: controller.signal })
      .then((stored) => setMessages(stored.map(toUIMessage)))
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Could not load this conversation.')
        }
      })
    return () => controller.abort()
  }, [threadId])

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
      </div>
    )
  }
  if (!messages) {
    return <div className="grid h-svh place-items-center text-sm text-muted-foreground">Loading conversation…</div>
  }
  return <ChatConversation threadId={threadId} initialMessages={messages} />
}

function toUIMessage(message: StoredChatMessage): DocumentUIMessage {
  return {
    id: message.id,
    role: message.role,
    parts: storedParts(message),
  }
}

function storedParts(message: StoredChatMessage): DocumentUIMessage['parts'] {
  if (typeof message.message_data !== 'object' || message.message_data === null) {
    return [{ type: 'text', text: message.content }]
  }
  const stored = message.message_data as Record<string, unknown>
  if (!Array.isArray(stored.parts)) return [{ type: 'text', text: message.content }]

  const parts: DocumentUIMessage['parts'] = []
  for (const part of stored.parts) {
    if (typeof part !== 'object' || part === null) continue
    const candidate = part as Record<string, unknown>
    if (candidate.type === 'text' && typeof candidate.text === 'string') {
      parts.push({ type: 'text', text: candidate.text })
    } else if (candidate.type === 'data-citation' && isCitationData(candidate.data)) {
      parts.push({ type: 'data-citation', data: candidate.data })
    } else if (candidate.type === 'data-answer-status' && isAnswerStatusData(candidate.data)) {
      parts.push({ type: 'data-answer-status', data: candidate.data })
    }
  }
  return parts.length ? parts : [{ type: 'text', text: message.content }]
}
