import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { File, Trash2, AlertCircle, CheckCircle, Loader2, Clock } from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { documentsApi } from '../services/api'
import type { Document } from '../types'

const STATUS_CONFIG = {
  uploaded: { label: 'Uploaded', icon: Clock, className: 'badge-gray' },
  processing: { label: 'Extracting', icon: Loader2, className: 'badge-yellow', spin: true },
  processed: { label: 'Ready', icon: CheckCircle, className: 'badge-green' },
  failed: { label: 'Failed', icon: AlertCircle, className: 'badge-red' },
}

const TYPE_ICONS: Record<string, string> = {
  pdf: '📄',
  excel: '📊',
  csv: '📋',
  docx: '📝',
  image: '🖼',
  unknown: '📁',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentList() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
    refetchInterval: (query) => {
      const docs = query.state.data?.documents ?? []
      const hasProcessing = docs.some((d) => d.status === 'processing' || d.status === 'uploaded')
      return hasProcessing ? 3000 : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['financial-summary'] })
      toast.success('Document deleted')
    },
    onError: () => toast.error('Failed to delete document'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="text-center py-8 text-red-500 text-sm">
        Failed to load documents. Is the backend running?
      </div>
    )
  }

  const docs = data?.documents ?? []

  if (docs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        No documents yet. Upload files above to begin.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {docs.map((doc) => (
        <DocumentRow
          key={doc.id}
          document={doc}
          onDelete={() => deleteMutation.mutate(doc.id)}
          deleting={deleteMutation.isPending}
        />
      ))}
    </div>
  )
}

function DocumentRow({
  document: doc,
  onDelete,
  deleting,
}: {
  document: Document
  onDelete: () => void
  deleting: boolean
}) {
  const config = STATUS_CONFIG[doc.status]
  const StatusIcon = config.icon

  return (
    <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-gray-300 transition-colors">
      <span className="text-2xl shrink-0">{TYPE_ICONS[doc.document_type] || '📁'}</span>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{doc.original_filename}</p>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
          <span>{formatBytes(doc.file_size)}</span>
          {doc.page_count && <span>• {doc.page_count} pages</span>}
          {doc.extraction_confidence && (
            <span>• {(doc.extraction_confidence * 100).toFixed(0)}% confidence</span>
          )}
        </div>
      </div>

      <div className={clsx('badge', config.className, 'flex items-center gap-1 shrink-0')}>
        <StatusIcon
          className={clsx('h-3 w-3', 'spin' in config && config.spin && 'animate-spin')}
        />
        {config.label}
      </div>

      <button
        onClick={onDelete}
        disabled={deleting}
        className="text-gray-400 hover:text-red-500 transition-colors p-1"
        title="Delete document"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  )
}
