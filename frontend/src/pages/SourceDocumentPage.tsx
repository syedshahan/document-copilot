import { ArrowLeft, ExternalLink } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { documents, type DocumentLocation } from '@/lib/api'

export function SourceDocumentPage() {
  const { documentId, chunkId } = useParams<{ documentId: string; chunkId: string }>()
  const [document, setDocument] = useState<DocumentLocation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const citationRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!documentId || !chunkId) return
    const controller = new AbortController()
    void documents
      .getLocation(documentId, chunkId, { signal: controller.signal, timeoutMs: 30_000 })
      .then(setDocument)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Could not load the filing.')
        }
      })
    return () => controller.abort()
  }, [chunkId, documentId])

  useEffect(() => {
    if (document) citationRef.current?.scrollIntoView({ block: 'center' })
  }, [document])

  if (error) return <div className="p-8"><Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert></div>
  if (!document) return <div className="grid min-h-svh place-items-center text-sm text-muted-foreground">Loading cited filing…</div>

  const before = document.highlight_start === null ? '' : document.content.slice(0, document.highlight_start)
  const cited = document.highlight_start === null ? document.chunk_content : document.content.slice(document.highlight_start, document.highlight_end ?? undefined)
  const after = document.highlight_end === null ? '' : document.content.slice(document.highlight_end)

  return (
    <main className="min-h-svh bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b bg-background/95 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <Button asChild variant="ghost" size="icon"><Link to="/chats" aria-label="Back to conversations"><ArrowLeft /></Link></Button>
            <div className="min-w-0">
              <h1 className="m-0 truncate text-lg font-semibold">{document.company_name} · {document.filing_type} {document.fiscal_year}</h1>
              <p className="truncate text-sm text-muted-foreground">{document.section || 'Filing'}{document.page ? ` · Page ${document.page}` : ''} · {document.accession_number}</p>
            </div>
          </div>
          <Button asChild variant="outline"><a href={document.source_url} target="_blank" rel="noreferrer"><ExternalLink />Official SEC filing</a></Button>
        </div>
      </header>
      <article className="mx-auto max-w-5xl whitespace-pre-wrap px-6 py-10 font-mono text-sm leading-7">
        {document.highlight_start === null ? null : before}
        <mark ref={citationRef} className="rounded bg-yellow-200 px-1 text-black ring-4 ring-yellow-200/40">{cited}</mark>
        {document.highlight_end === null ? null : after}
      </article>
    </main>
  )
}
