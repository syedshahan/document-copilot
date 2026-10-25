import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { ArrowUp, Bot, UserRound } from 'lucide-react'
import { useMemo, useState } from 'react'

import { CitationChip } from '@/components/chat/CitationChip'
import { SourcePassagePanel } from '@/components/chat/SourcePassagePanel'
import type { CitationData, DocumentUIMessage } from '@/components/chat/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

type ChatConversationProps = {
  threadId: string
  initialMessages: DocumentUIMessage[]
}

export function ChatConversation({ threadId, initialMessages }: ChatConversationProps) {
  const [input, setInput] = useState('')
  const [selectedCitation, setSelectedCitation] = useState<CitationData | null>(null)
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
        body: { threadId },
        headers: async (): Promise<Record<string, string>> => {
          const token = await getAccessToken()
          return token ? { Authorization: `Bearer ${token}` } : {}
        },
      }),
    [threadId],
  )
  const { messages, sendMessage, status, error } = useChat<DocumentUIMessage>({
    id: threadId,
    messages: initialMessages,
    transport,
  })
  const isBusy = status === 'submitted' || status === 'streaming'

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (!text || isBusy) return
    setInput('')
    void sendMessage({ text })
  }

  return (
    <div className="relative flex h-svh min-w-0">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b px-6 py-4">
          <h1 className="m-0 text-lg font-semibold tracking-normal">Conversation</h1>
          <p className="text-sm text-muted-foreground">Grounded answers from your SEC filing corpus.</p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="mx-auto max-w-3xl space-y-6">
            {!messages.length ? (
              <div className="grid min-h-80 place-items-center text-center">
                <div>
                  <Bot className="mx-auto mb-4 size-10 text-muted-foreground" />
                  <h2 className="text-xl font-semibold">Start your research conversation</h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Ask about a company, filing period, financial metric, or disclosed risk.
                  </p>
                </div>
              </div>
            ) : null}

            {messages.map((message) => (
              <article key={message.id} className="flex gap-3">
                <div className="grid size-8 shrink-0 place-items-center rounded-full bg-muted">
                  {message.role === 'user' ? <UserRound className="size-4" /> : <Bot className="size-4" />}
                </div>
                <div className="min-w-0 flex-1 pt-1">
                  <p className="mb-1 text-sm font-medium">
                    {message.role === 'user' ? 'You' : 'Document Copilot'}
                  </p>
                  {message.parts.map((part, index) => {
                    if (part.type === 'text') {
                      return <p key={`${message.id}-${index}`} className="whitespace-pre-wrap text-sm leading-6">{part.text}</p>
                    }
                    if (part.type === 'data-citation') {
                      return (
                        <span key={`${message.id}-${index}`} className="mt-2 mr-2 inline-flex">
                          <CitationChip
                            citation={part.data}
                            number={citationNumber(message.parts, index)}
                            isSelected={selectedCitation?.chunk_id === part.data.chunk_id}
                            onSelect={() => setSelectedCitation(part.data)}
                          />
                        </span>
                      )
                    }
                    if (part.type === 'data-answer-status') {
                      return (
                        <Alert key={`${message.id}-${index}`} className="mt-3">
                          <AlertDescription>
                            The available corpus did not contain enough evidence for a grounded answer. Add a company, period, or metric and try again.
                          </AlertDescription>
                        </Alert>
                      )
                    }
                    return null
                  })}
                </div>
              </article>
            ))}

            {status === 'submitted' ? <p className="animate-pulse text-sm text-muted-foreground">Searching filings and checking sources…</p> : null}
            {status === 'streaming' ? <p className="animate-pulse text-sm text-muted-foreground">Writing grounded answer…</p> : null}
            {error ? <Alert variant="destructive"><AlertDescription>{friendlyChatError(error)}</AlertDescription></Alert> : null}
          </div>
        </div>

        <div className="border-t bg-background px-6 py-4">
          <form className="mx-auto flex max-w-3xl gap-2" onSubmit={handleSubmit}>
            <Input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask about a filing…" aria-label="Message" disabled={isBusy} autoFocus />
            <Button type="submit" size="icon" disabled={!input.trim() || isBusy} aria-label="Send message"><ArrowUp className="size-4" /></Button>
          </form>
        </div>
      </div>

      {selectedCitation ? (
        <div className="absolute inset-0 z-20 bg-background lg:static lg:w-[26rem]">
          <SourcePassagePanel citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
        </div>
      ) : null}
    </div>
  )
}

function citationNumber(parts: DocumentUIMessage['parts'], throughIndex: number): number {
  return parts.slice(0, throughIndex + 1).filter((part) => part.type === 'data-citation').length
}

function friendlyChatError(error: Error): string {
  const message = error.message.toLowerCase()
  if (message.includes('401') || message.includes('unauthorized')) return 'Your session expired. Sign in again and retry.'
  if (message.includes('network') || message.includes('fetch')) return 'Could not reach Document Copilot. Check the backend and CORS settings.'
  if (message.includes('citation') || message.includes('grounding')) return 'The answer could not be verified against its sources. Please retry.'
  return 'Document Copilot could not complete this answer. Please retry in a moment.'
}
