import { useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import DiagnosticsPanel from './DiagnosticsPanel'

const MD_COMPONENTS = {
  h1: ({children}) => <h1 className="text-base font-bold text-slate-100 mt-4 mb-2 first:mt-0">{children}</h1>,
  h2: ({children}) => <h2 className="text-sm font-semibold text-slate-200 mt-4 mb-1.5 first:mt-0">{children}</h2>,
  h3: ({children}) => <h3 className="text-sm font-medium text-slate-300 mt-3 mb-1 first:mt-0">{children}</h3>,
  p: ({children}) => <p className="mb-3 last:mb-0">{children}</p>,
  strong: ({children}) => <strong className="font-semibold text-slate-100">{children}</strong>,
  em: ({children}) => <em className="italic text-slate-400">{children}</em>,
  ul: ({children}) => <ul className="mb-3 space-y-1 pl-4 list-disc list-outside">{children}</ul>,
  ol: ({children}) => <ol className="mb-3 space-y-1 pl-4 list-decimal list-outside">{children}</ol>,
  li: ({children}) => <li className="text-slate-300">{children}</li>,
  code: ({children}) => <code className="font-mono text-xs bg-ink-700 text-amber-400/80 px-1 py-0.5 rounded">{children}</code>,
  blockquote: ({children}) => <blockquote className="border-l border-slate-600 pl-3 my-2 text-slate-500 italic">{children}</blockquote>,
}

// messages: array of { question: string, result: { answer, sources, chunks_used, memory_updated, budget, diagnostics } }
export default function AskPanel({ messages, loading, onSelectDecision, onNewConversation }) {
  const bottomRef = useRef(null)

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!loading && messages.length === 0) return null

  const handleExport = () => {
    const lines = messages.map(({ question, result }, i) => {
      const sources = result.sources?.length
        ? `### Sources\n${result.sources.map(s => `- [${s.citation}] ${s.title}`).join('\n')}`
        : ''
      return `## Q${i + 1}: ${question}\n\n${result.answer}\n\n${sources}`
    })
    const md = `# MCFD Files Research\n\n${lines.join('\n\n---\n\n')}`
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mcfd-research.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  const hasContent = messages.some(m => m.result?.answer)

  return (
    <div className="mt-6 space-y-6">

      {/* Thread controls */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-sky-400/70 tracking-widest uppercase">
          Ask · {messages.length} {messages.length === 1 ? 'question' : 'questions'}
        </span>
        <div className="flex items-center gap-2">
          {!loading && hasContent && (
            <button
              onClick={handleExport}
              className="font-mono text-[10px] text-slate-600 hover:text-slate-300 border border-ink-600 hover:border-ink-500 px-2 py-1 rounded transition-colors"
            >
              EXPORT .MD
            </button>
          )}
          <button
            onClick={onNewConversation}
            className="font-mono text-[10px] text-slate-600 hover:text-sky-400 border border-ink-600 hover:border-sky-500/30 px-2 py-1 rounded transition-colors"
          >
            NEW CONVERSATION
          </button>
        </div>
      </div>

      {/* Message thread */}
      {messages.map(({ question, result }, idx) => {
        const isLast = idx === messages.length - 1
        const isStreaming = isLast && loading

        return (
          <div key={idx}>
            {/* Question bubble */}
            <div className="flex justify-end mb-4">
              <div className="max-w-[85%] bg-ink-700 border border-ink-600 rounded-lg px-4 py-2.5">
                <p className="font-mono text-xs text-slate-300">{question}</p>
              </div>
            </div>

            {/* Answer block */}
            <div className="border-l-2 border-sky-500/50 pl-4">
              <div className="flex items-center gap-2 mb-3">
                {isStreaming ? (
                  <span className="font-mono text-[10px] text-sky-400/60 tracking-widest uppercase flex items-center gap-2">
                    Streaming
                    <span className="flex gap-1">
                      {[0, 1, 2].map(i => (
                        <span
                          key={i}
                          className="inline-block w-1 h-1 rounded-full bg-sky-400/60 animate-pulse"
                          style={{ animationDelay: `${i * 200}ms` }}
                        />
                      ))}
                    </span>
                  </span>
                ) : (
                  <span className="font-mono text-[10px] text-sky-400/70 tracking-widest uppercase">
                    Analysis · {result.chunks_used} source chunks
                  </span>
                )}
                {!isStreaming && result.memory_updated && (
                  <span className="font-mono text-[10px] text-emerald-500/50 tracking-widest">
                    · R2 ✓
                  </span>
                )}
              </div>

              <div className="prose-answer text-sm text-slate-300 leading-relaxed">
                <ReactMarkdown components={MD_COMPONENTS}>
                  {result.answer + (isStreaming ? '▋' : '')}
                </ReactMarkdown>
              </div>

              {!isStreaming && (
                <DiagnosticsPanel budget={result.budget} diagnostics={result.diagnostics} />
              )}

              {/* Sources */}
              {!isStreaming && result.sources?.length > 0 && (
                <div className="mt-3">
                  <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">
                    Cited Sources
                  </p>
                  <div className="space-y-2">
                    {result.sources.map(src => (
                      <button
                        key={src.decision_id}
                        onClick={() => onSelectDecision(src.decision_id)}
                        className="w-full text-left flex items-start gap-3 border border-ink-600 hover:border-amber-500/30 rounded px-3 py-2.5 bg-ink-800 hover:bg-ink-700 transition-colors group"
                      >
                        <span className="font-mono text-[10px] text-amber-500/70 group-hover:text-amber-400 transition-colors mt-0.5 flex-shrink-0">
                          [{src.citation}]
                        </span>
                        <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors leading-snug">
                          {src.title}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {!isStreaming && result.sources?.length === 0 && (
                <p className="font-mono text-[10px] text-slate-700 italic mt-2">
                  No directly cited sources extracted.
                </p>
              )}
            </div>

            {/* Divider between messages */}
            {idx < messages.length - 1 && (
              <div className="border-t border-ink-600/30 mt-6" />
            )}
          </div>
        )
      })}

      <div ref={bottomRef} />
    </div>
  )
}
