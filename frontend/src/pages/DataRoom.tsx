import React from 'react'
import { FileUpload } from '../components/FileUpload'
import { DocumentList } from '../components/DocumentList'
import { Upload, Database } from 'lucide-react'

export function DataRoom() {
  return (
    <div className="space-y-6">
      {/* Upload zone */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Upload className="h-5 w-5 text-brand-500" />
          <h2 className="text-base font-semibold text-gray-900">Upload Documents</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Upload financial statements, management accounts, cap tables, KPIs, and any other
          documents. The system will automatically extract structured financial data.
        </p>
        <FileUpload />
      </div>

      {/* Document library */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-brand-500" />
          <h2 className="text-base font-semibold text-gray-900">Document Library</h2>
        </div>
        <DocumentList />
      </div>
    </div>
  )
}
