import { Fragment, type ReactNode } from 'react'

export function AnswerContent({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).filter(Boolean)
  return (
    <div className="space-y-3 text-[0.9375rem] leading-7 text-foreground/90">
      {blocks.map((block, index) => {
        const lines = block.split('\n')
        if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
          return (
            <ul key={index} className="ml-5 list-disc space-y-1.5 marker:text-primary/70">
              {lines.map((line, lineIndex) => <li key={lineIndex}>{formatInline(line.replace(/^\s*[-*]\s+/, ''))}</li>)}
            </ul>
          )
        }
        return <p key={index} className="whitespace-pre-wrap">{formatInline(block)}</p>
      })}
    </div>
  )
}

function formatInline(text: string): ReactNode[] {
  return text.split(/(\*\*.*?\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={index} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>
    ) : <Fragment key={index}>{part}</Fragment>,
  )
}
