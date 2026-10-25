import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { ArrowUp, Bot, Database, Search, ShieldCheck, UserRound } from 'lucide-react'
import { useMemo, useState } from 'react'

import { AnswerContent } from '@/components/chat/AnswerContent'
import { CitationChip } from '@/components/chat/CitationChip'
import { SourcePassagePanel } from '@/components/chat/SourcePassagePanel'
import type { CitationData, DocumentUIMessage } from '@/components/chat/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

export function ChatConversation({ threadId, initialMessages }: { threadId: string; initialMessages: DocumentUIMessage[] }) {
  const [input, setInput] = useState('')
  const [selectedCitation, setSelectedCitation] = useState<CitationData | null>(null)
  const transport = useMemo(() => new DefaultChatTransport({
    api: `${env.apiBaseUrl}/chat/stream`, body: { threadId },
    headers: async (): Promise<Record<string, string>> => {
      const token = await getAccessToken()
      return token ? { Authorization: `Bearer ${token}` } : {}
    },
  }), [threadId])
  const { messages, sendMessage, status, error } = useChat<DocumentUIMessage>({ id: threadId, messages: initialMessages, transport })
  const isBusy = status === 'submitted' || status === 'streaming'

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (!text || isBusy) return
    setInput('')
    void sendMessage({ text })
  }

  return (
    <div className="relative flex h-svh min-w-0 bg-[radial-gradient(circle_at_top,_white_0,_transparent_42%)]">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b bg-white/70 px-5 py-4 backdrop-blur-xl md:px-10">
          <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
            <div><h1 className="text-lg font-semibold tracking-tight">Research conversation</h1><p className="mt-0.5 text-sm text-muted-foreground">Ask, verify, and jump straight to the filing evidence.</p></div>
            <div className="hidden items-center gap-2 rounded-full border bg-white px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-sm sm:flex"><span className="size-2 rounded-full bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.12)]" />Corpus connected</div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-8 md:px-10 md:py-10">
          <div className="mx-auto max-w-4xl space-y-7">
            {!messages.length ? <EmptyState /> : null}
            {messages.filter(hasVisibleContent).map((message) => (
              <article key={message.id} className={`flex gap-3.5 ${message.role === 'user' ? 'justify-end' : ''}`}>
                {message.role !== 'user' ? <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/15"><Bot className="size-4" /></div> : null}
                <div className={`min-w-0 ${message.role === 'user' ? 'max-w-[80%]' : 'max-w-[calc(100%-3rem)] flex-1'}`}>
                  <p className={`mb-1.5 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground ${message.role === 'user' ? 'text-right' : ''}`}>{message.role === 'user' ? 'You' : 'Document Copilot'}</p>
                  <div className={message.role === 'user' ? 'rounded-2xl rounded-tr-md bg-primary px-4 py-2.5 text-sm leading-6 text-primary-foreground shadow-sm' : 'rounded-2xl rounded-tl-md border bg-white p-5 shadow-sm'}>
                    {message.parts.map((part, index) => {
                      if (part.type === 'text') return message.role === 'user' ? <p key={`${message.id}-${index}`}>{part.text}</p> : <AnswerContent key={`${message.id}-${index}`} text={part.text} />
                      if (part.type === 'data-citation') return <span key={`${message.id}-${index}`} className="mt-4 mr-2 inline-flex"><CitationChip citation={part.data} number={citationNumber(message.parts, index)} isSelected={selectedCitation?.chunk_id === part.data.chunk_id} onSelect={() => setSelectedCitation(part.data)} /></span>
                      if (part.type === 'data-answer-status') return <Alert key={`${message.id}-${index}`} className="mt-4 border-amber-200 bg-amber-50/80 text-amber-950"><AlertDescription><span className="flex gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0" />The available corpus did not contain enough evidence for a grounded answer. Add a company, period, or metric and try again.</span></AlertDescription></Alert>
                      return null
                    })}
                  </div>
                </div>
                {message.role === 'user' ? <div className="grid size-9 shrink-0 place-items-center rounded-xl border bg-white text-muted-foreground shadow-sm"><UserRound className="size-4" /></div> : null}
              </article>
            ))}
            {status === 'submitted' ? <ProgressState label="Searching filings and checking sources…" /> : null}
            {status === 'streaming' ? <ProgressState label="Writing grounded answer…" /> : null}
            {error ? <Alert variant="destructive"><AlertDescription>{friendlyChatError(error)}</AlertDescription></Alert> : null}
          </div>
        </div>

        <div className="border-t bg-white/80 px-4 py-4 backdrop-blur-xl md:px-10">
          <form className="mx-auto flex max-w-4xl items-center gap-2 rounded-2xl border bg-white p-2 shadow-[0_12px_40px_rgba(30,41,59,0.09)] focus-within:border-primary/40 focus-within:ring-4 focus-within:ring-primary/5" onSubmit={handleSubmit}>
            <Input className="h-11 flex-1 border-0 bg-transparent px-3 shadow-none focus-visible:ring-0" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question about the filing…" aria-label="Message" disabled={isBusy} autoFocus />
            <Button className="size-10 rounded-xl shadow-md shadow-primary/20" type="submit" size="icon" disabled={!input.trim() || isBusy} aria-label="Send message"><ArrowUp className="size-4" /></Button>
          </form>
          <p className="mx-auto mt-2 max-w-4xl text-center text-[0.6875rem] text-muted-foreground">Answers are grounded in your filing corpus. Verify important decisions against the original source.</p>
        </div>
      </div>
      {selectedCitation ? <div className="absolute inset-0 z-20 bg-background xl:static xl:w-[28rem]"><SourcePassagePanel citation={selectedCitation} onClose={() => setSelectedCitation(null)} /></div> : null}
    </div>
  )
}

function EmptyState() {
  return <div className="grid min-h-[60vh] place-items-center text-center"><div className="max-w-lg"><div className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-xl shadow-primary/20"><Search className="size-6" /></div><h2 className="text-2xl font-semibold tracking-tight">Research the filing, not the noise</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Ask about a company, filing period, financial metric, or disclosed risk.</p><div className="mt-6 flex justify-center gap-5 text-xs text-muted-foreground"><span className="flex items-center gap-1.5"><Database className="size-3.5" />Filing grounded</span><span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5" />Citation checked</span></div></div></div>
}

function ProgressState({ label }: { label: string }) {
  return <div className="flex items-center gap-3 pl-12 text-sm text-muted-foreground"><span className="flex gap-1"><i className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-200ms]" /><i className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-100ms]" /><i className="size-1.5 animate-bounce rounded-full bg-primary" /></span>{label}</div>
}

function citationNumber(parts: DocumentUIMessage['parts'], throughIndex: number) { return parts.slice(0, throughIndex + 1).filter((part) => part.type === 'data-citation').length }
function hasVisibleContent(message: DocumentUIMessage) { return message.parts.some((part) => (part.type === 'text' && part.text.trim().length > 0) || part.type === 'data-citation' || part.type === 'data-answer-status') }
function friendlyChatError(error: Error) {
  const message = error.message.toLowerCase()
  if (message.includes('401') || message.includes('unauthorized')) return 'Your session expired. Sign in again and retry.'
  if (message.includes('network') || message.includes('fetch')) return 'Could not reach Document Copilot. Check the backend and CORS settings.'
  return 'Document Copilot could not complete this answer. Please retry in a moment.'
}
