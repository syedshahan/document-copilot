import { BookOpen, CalendarDays, Check, Copy, ExternalLink, Hash, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { CitationData } from '@/components/chat/types'
import { Button } from '@/components/ui/button'

type SourcePassagePanelProps = {
  citation: CitationData
  onClose: () => void
}

export function SourcePassagePanel({ citation, onClose }: SourcePassagePanelProps) {
  const [copied, setCopied] = useState(false)
  const { metadata } = citation
  const location = metadata.page ? `Page ${metadata.page}` : metadata.section || 'Location unavailable'

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l bg-white shadow-[-16px_0_40px_rgba(30,41,59,0.08)]" aria-label="Source passage">
      <header className="flex items-start justify-between gap-4 border-b bg-white/90 px-6 py-5 backdrop-blur-xl">
        <div className="min-w-0">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-primary">Verified source</p>
          <h2 className="mt-1 truncate text-lg font-semibold tracking-tight">
            {metadata.company_name || metadata.ticker || 'SEC filing'}
          </h2>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close source passage">
          <X className="size-4" />
        </Button>
      </header>

      <div className="space-y-6 overflow-y-auto p-6">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <SourceFact icon={<BookOpen />} label="Filing" value={filingLabel(citation)} />
          <SourceFact icon={<CalendarDays />} label="Filed" value={formatDate(metadata.filing_date)} />
          <SourceFact icon={<Hash />} label="Location" value={location} />
          <SourceFact icon={<Hash />} label="Accession" value={metadata.accession_number || 'Unavailable'} />
        </dl>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Exact stored text</p>
          <blockquote className="whitespace-pre-wrap rounded-xl border-l-4 border-l-primary bg-muted/45 p-5 text-sm leading-7 shadow-sm">
            {citation.excerpt}
          </blockquote>
        </div>

        <div className="flex flex-wrap gap-2 border-t pt-4">
          {metadata.document_id ? (
            <Button asChild>
              <Link to={`/sources/${metadata.document_id}/${citation.chunk_id}`}>
                <ExternalLink className="size-4" />
                Open exact cited location
              </Link>
            </Button>
          ) : null}
          {metadata.source_url ? (
            <Button asChild variant="outline">
              <a href={metadata.source_url} target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" />
                Official SEC filing
              </a>
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void navigator.clipboard.writeText(citation.excerpt).then(() => {
                setCopied(true)
                window.setTimeout(() => setCopied(false), 2000)
              })
            }}
          >
            {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            {copied ? 'Copied' : 'Copy passage'}
          </Button>
        </div>
      </div>
    </aside>
  )
}

function SourceFact({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border bg-muted/30 p-3.5">
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground [&_svg]:size-3.5">{icon}{label}</dt>
      <dd className="mt-1 truncate font-medium" title={value}>{value}</dd>
    </div>
  )
}

function filingLabel(citation: CitationData): string {
  const { metadata } = citation
  return [metadata.ticker, metadata.filing_type, metadata.fiscal_year].filter(Boolean).join(' ') || 'SEC filing'
}

function formatDate(value?: string): string {
  if (!value) return 'Unavailable'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value))
}
