import type { UIMessage } from 'ai'

export type CitationMetadata = {
  ticker?: string
  company_name?: string
  filing_type?: string
  filing_date?: string
  fiscal_year?: number
  accession_number?: string
  page?: number | null
  section?: string | null
  source_start?: number
  source_end?: number
  source_url?: string
}

export type CitationData = {
  chunk_id: string
  excerpt: string
  metadata: CitationMetadata
}

export type AnswerStatusData = { kind: 'insufficient-evidence' }

export type DocumentUIMessage = UIMessage<
  unknown,
  { citation: CitationData; 'answer-status': AnswerStatusData }
>

export function isCitationData(value: unknown): value is CitationData {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.chunk_id === 'string' &&
    typeof candidate.excerpt === 'string' &&
    typeof candidate.metadata === 'object' &&
    candidate.metadata !== null
  )
}

export function isAnswerStatusData(value: unknown): value is AnswerStatusData {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as Record<string, unknown>).kind === 'insufficient-evidence'
  )
}
