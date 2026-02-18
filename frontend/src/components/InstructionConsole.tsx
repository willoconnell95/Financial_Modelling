import React, { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Terminal, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { modelsApi } from '../services/api'
import { useAppStore } from '../store/appStore'
import type { CommandResult } from '../types'

const EXAMPLE_COMMANDS = [
  'Model revenue using a 3-year CAGR from historicals',
  'Apply a 15% staff cost increase from FY25',
  'Add a scenario where churn increases by 20%',
  'Build a monthly cashflow forecast for 36 months',
  'Run sensitivity analysis on revenue',
  'Apply a 10% growth rate to revenue over 3 years',
  'Set tax rate to 25%',
  'Apply a 5% cost growth',
]

interface LogEntry {
  type: 'user' | 'system' | 'success' | 'error'
  text: string
  detail?: string
  timestamp: string
}

export function InstructionConsole() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [log, setLog] = useState<LogEntry[]>([
    {
      type: 'system',
      text: 'Financial Modelling Console ready. Type a natural-language command to update your model.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ])
  const [showExamples, setShowExamples] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)
  const { activeModelId, activeScenarioId, setModelOutput, addCommandToHistory } = useAppStore()

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  const appendLog = (entry: Omit<LogEntry, 'timestamp'>) => {
    setLog((prev) => [...prev, { ...entry, timestamp: new Date().toLocaleTimeString() }])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cmd = input.trim()
    if (!cmd || loading) return

    if (!activeModelId) {
      toast.error('Please create or select a model first.')
      return
    }

    setInput('')
    appendLog({ type: 'user', text: cmd })
    setLoading(true)

    try {
      const result: CommandResult = await modelsApi.executeCommand({
        command: cmd,
        model_state_id: activeModelId,
        scenario_id: activeScenarioId ?? undefined,
      })

      addCommandToHistory(cmd)

      if (result.success) {
        appendLog({
          type: 'success',
          text: `✓ ${result.interpreted_as}`,
          detail: result.operations_performed.join(' • '),
        })
        if (result.model_output) {
          setModelOutput(result.model_output)
        }
      } else {
        appendLog({
          type: 'error',
          text: `✗ ${result.message}`,
          detail: result.errors.join('; '),
        })
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Command failed'
      appendLog({ type: 'error', text: message })
    } finally {
      setLoading(false)
    }
  }

  const useExample = (example: string) => {
    setInput(example)
    setShowExamples(false)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Log area */}
      <div className="flex-1 overflow-y-auto bg-gray-950 rounded-t-xl p-4 font-mono text-xs space-y-2 min-h-[280px] max-h-[400px]">
        {log.map((entry, idx) => (
          <LogLine key={idx} entry={entry} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-yellow-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Processing command…</span>
          </div>
        )}
        <div ref={logEndRef} />
      </div>

      {/* Input area */}
      <div className="bg-gray-900 rounded-b-xl border-t border-gray-700 p-3 space-y-2">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="flex items-center gap-2 flex-1 bg-gray-800 rounded-lg px-3 py-2">
            <Terminal className="h-3.5 w-3.5 text-gray-400 shrink-0" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a modelling instruction…"
              className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 outline-none"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || loading || !activeModelId}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5',
              input.trim() && activeModelId && !loading
                ? 'bg-brand-600 text-white hover:bg-brand-700'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            )}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Run
          </button>
        </form>

        {/* Examples toggle */}
        <div>
          <button
            onClick={() => setShowExamples((v) => !v)}
            className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
          >
            <ChevronDown
              className={clsx('h-3 w-3 transition-transform', showExamples && 'rotate-180')}
            />
            Example commands
          </button>
          {showExamples && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {EXAMPLE_COMMANDS.map((ex) => (
                <button
                  key={ex}
                  onClick={() => useExample(ex)}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-1 rounded border border-gray-700 transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function LogLine({ entry }: { entry: LogEntry }) {
  const styles: Record<string, string> = {
    user: 'text-cyan-400',
    system: 'text-gray-400',
    success: 'text-green-400',
    error: 'text-red-400',
  }
  const prefixes: Record<string, string> = {
    user: '> ',
    system: '# ',
    success: '',
    error: '',
  }

  return (
    <div>
      <div className={clsx('flex gap-2', styles[entry.type])}>
        <span className="text-gray-600 shrink-0">[{entry.timestamp}]</span>
        <span>
          {prefixes[entry.type]}
          {entry.text}
        </span>
      </div>
      {entry.detail && (
        <div className="ml-14 text-gray-500 text-xs">{entry.detail}</div>
      )}
    </div>
  )
}
