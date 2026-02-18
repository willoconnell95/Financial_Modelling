import { useState, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Send, Terminal, CheckCircle, XCircle, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react'
import { modellingApi } from '../services/api'
import type { CommandHistory } from '../types'
import clsx from 'clsx'

const EXAMPLE_COMMANDS = [
  'Model revenue using a 15% CAGR',
  'Apply a 10% staff cost increase from FY25',
  'Set gross margin to 65%',
  'Build a monthly cashflow forecast for 36 months',
  'Add a scenario where churn increases by 20%',
  'Set tax rate to 25%',
  'Grow operating expenses at 8% per year',
  'Run a sensitivity analysis on revenue growth vs EBITDA',
]

interface Props {
  scenario: string
  onCommandSuccess?: () => void
}

export default function InstructionConsole({ scenario, onCommandSuccess }: Props) {
  const [command, setCommand] = useState('')
  const [executing, setExecuting] = useState(false)
  const [showExamples, setShowExamples] = useState(false)
  const [historyExpanded, setHistoryExpanded] = useState(true)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  const { data: history = [] } = useQuery<CommandHistory[]>({
    queryKey: ['commandHistory'],
    queryFn: modellingApi.getCommandHistory,
    refetchInterval: executing ? 2000 : 30000,
  })

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    const cmd = command.trim()
    if (!cmd || executing) return

    setExecuting(true)
    try {
      const result = await modellingApi.executeCommand(cmd, scenario)

      if (result.status === 'success') {
        toast.success(result.explanation || 'Command executed')
        queryClient.invalidateQueries({ queryKey: ['modelSummary'] })
        queryClient.invalidateQueries({ queryKey: ['chartData'] })
        queryClient.invalidateQueries({ queryKey: ['commandHistory'] })
        onCommandSuccess?.()
        setCommand('')
      } else {
        toast.error(result.explanation || 'Command failed')
        if (result.suggestion) {
          toast(result.suggestion, { duration: 6000 })
        }
        queryClient.invalidateQueries({ queryKey: ['commandHistory'] })
      }
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to execute command'
      toast.error(message)
    } finally {
      setExecuting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const selectExample = (ex: string) => {
    setCommand(ex)
    setShowExamples(false)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Input area */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='Type a modelling instruction... e.g. "Model revenue using 15% CAGR"'
            rows={3}
            disabled={executing}
            className={clsx(
              'w-full resize-none rounded-lg border text-sm p-3 pr-10 font-mono',
              'bg-slate-900 text-green-400 placeholder-slate-600 border-slate-700',
              'focus:outline-none focus:ring-2 focus:ring-blue-500',
              executing && 'opacity-60 cursor-not-allowed'
            )}
          />
          <button
            type="submit"
            disabled={!command.trim() || executing}
            className={clsx(
              'absolute bottom-2 right-2 p-1.5 rounded-md transition',
              command.trim() && !executing
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
            )}
            title="Execute (Enter)"
          >
            {executing ? (
              <div className="w-4 h-4 border-2 border-slate-400 border-t-white rounded-full animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setShowExamples(!showExamples)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-blue-500 transition"
          >
            <Lightbulb size={12} />
            Example commands
            {showExamples ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          <span className="text-xs text-slate-500">
            Scenario: <span className="text-blue-400 font-medium">{scenario}</span>
          </span>
        </div>

        {showExamples && (
          <div className="flex flex-col gap-1 bg-slate-800 rounded-lg p-2">
            {EXAMPLE_COMMANDS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => selectExample(ex)}
                className="text-left text-xs text-green-400 hover:text-green-300 hover:bg-slate-700 rounded px-2 py-1 transition font-mono"
              >
                &gt; {ex}
              </button>
            ))}
          </div>
        )}
      </form>

      {/* Command history */}
      <div>
        <button
          onClick={() => setHistoryExpanded(!historyExpanded)}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition mb-1"
        >
          <Terminal size={12} />
          Command History ({history.length})
          {historyExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {historyExpanded && (
          <div className="flex flex-col gap-1 max-h-72 overflow-y-auto scrollbar-thin">
            {history.length === 0 && (
              <p className="text-xs text-slate-400 py-1">No commands yet.</p>
            )}
            {history.map((entry) => (
              <div
                key={entry.id}
                className={clsx(
                  'rounded-md p-2 text-xs border',
                  entry.status === 'success'
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                )}
              >
                <div className="flex items-start gap-1.5">
                  {entry.status === 'success' ? (
                    <CheckCircle size={12} className="text-green-600 mt-0.5 flex-shrink-0" />
                  ) : (
                    <XCircle size={12} className="text-red-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-slate-800 truncate">{entry.command}</p>
                    {entry.result_summary && (
                      <p className="text-slate-500 mt-0.5 truncate">{entry.result_summary}</p>
                    )}
                    <p className="text-slate-400 mt-0.5">
                      {new Date(entry.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
