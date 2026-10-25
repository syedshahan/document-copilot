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
      className="h-auto max-w-full justify-start rounded-lg border-primary/15 bg-primary/5 px-2.5 py-1.5 text-left text-primary shadow-none hover:border-primary/30 hover:bg-primary/10"
      onClick={onSelect}
      aria-label={`Open citation ${number}: ${filing}, ${location}`}
      aria-pressed={isSelected}
    >
      <span className="grid size-5 shrink-0 place-items-center rounded-md bg-primary text-[0.65rem] font-bold text-primary-foreground">{number}</span>
      <FileText className="size-3.5" />
      <span className="truncate">{filing || 'Filing'} · {location}</span>
    </Button>
  )
}
