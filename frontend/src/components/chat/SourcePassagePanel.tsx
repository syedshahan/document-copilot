import { BookOpen, CalendarDays, Check, Copy, ExternalLink, Hash, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'

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
  const citationUrl = originalCitationUrl(citation)

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l bg-muted/25" aria-label="Source passage">
      <header className="flex items-start justify-between gap-4 border-b bg-background px-5 py-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Source passage</p>
          <h2 className="mt-1 truncate text-base font-semibold">
            {metadata.company_name || metadata.ticker || 'SEC filing'}
          </h2>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close source passage">
          <X className="size-4" />
        </Button>
      </header>

      <div className="space-y-5 overflow-y-auto p-5">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <SourceFact icon={<BookOpen />} label="Filing" value={filingLabel(citation)} />
          <SourceFact icon={<CalendarDays />} label="Filed" value={formatDate(metadata.filing_date)} />
          <SourceFact icon={<Hash />} label="Location" value={location} />
          <SourceFact icon={<Hash />} label="Accession" value={metadata.accession_number || 'Unavailable'} />
        </dl>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Exact stored text</p>
          <blockquote className="whitespace-pre-wrap rounded-lg border bg-background p-4 text-sm leading-6 shadow-sm">
            {citation.excerpt}
          </blockquote>
        </div>

        <div className="flex flex-wrap gap-2 border-t pt-4">
          {citationUrl ? (
            <Button asChild>
              <a href={citationUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" />
                Jump to cited text in SEC filing
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
    <div className="min-w-0 rounded-lg border bg-background p-3">
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

function originalCitationUrl(citation: CitationData): string | null {
  if (!citation.metadata.source_url) return null
  const phrase = citationPhrase(citation.excerpt) || citation.metadata.section
  if (!phrase) return citation.metadata.source_url
  const baseUrl = citation.metadata.source_url.split('#', 1)[0]
  return `${baseUrl}#:~:text=${encodeURIComponent(phrase)}`
}

function citationPhrase(excerpt: string): string | null {
  const lines = excerpt
    .split(/\r?\n/)
    .map((line) => cleanMarkdown(line))
    .filter((line) => line.length >= 40 && !/form 10-k\s+\d+$/i.test(line))

  const prose = lines.find((line) => /[.!?]/.test(line)) || lines[0]
  if (!prose) return null
  const firstSentence = prose.match(/^.{40,180}?[.!?](?:\s|$)/)?.[0] || prose
  return firstSentence.slice(0, 180).trim()
}

function cleanMarkdown(value: string): string {
  return value
    .replace(/^#+\s*/, '')
    .replace(/[*_`]/g, '')
    .replace(/\s*\|\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
