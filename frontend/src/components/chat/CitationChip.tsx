import { FileText } from 'lucide-react'

import type { CitationData } from '@/components/chat/types'
import { Button } from '@/components/ui/button'

type CitationChipProps = {
  citation: CitationData
  number: number
  isSelected: boolean
  onSelect: () => void
}

export function CitationChip({ citation, number, isSelected, onSelect }: CitationChipProps) {
  const { metadata } = citation
  const location = metadata.page ? `p. ${metadata.page}` : metadata.section || 'Source'
  const filing = [metadata.ticker, metadata.filing_type, metadata.fiscal_year]
    .filter(Boolean)
    .join(' ')

  return (
    <Button
      type="button"
      variant={isSelected ? 'secondary' : 'outline'}
      size="sm"
      className="h-auto max-w-full justify-start rounded-full px-3 py-1.5 text-left"
      onClick={onSelect}
      aria-label={`Open citation ${number}: ${filing}, ${location}`}
      aria-pressed={isSelected}
    >
      <FileText className="size-3.5" />
      <span className="truncate">[{number}] {filing || 'Filing'} · {location}</span>
    </Button>
  )
}
