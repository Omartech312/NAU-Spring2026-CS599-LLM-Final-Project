import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDocumentsStore } from '../store'
import { documentsAPI } from '../api/client'
import {
  Upload, FileText, X, CheckCircle2, AlertCircle,
  Loader2, ArrowRight, Info
} from 'lucide-react'

export default function UploadPage() {
  const navigate = useNavigate()
  const { uploadDocument, loading, error, clearError } = useDocumentsStore()
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    return () => clearError()
  }, [])

  const handleFileSelect = (file) => {
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'pdf' && ext !== 'tex') {
      alert('Only PDF or LaTeX (.tex) files are allowed')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      alert('File size must be less than 50MB')
      return
    }
    setSelectedFile(file)
    if (!title) {
      const name = file.name.replace(/\.pdf$/i, '')
      setTitle(name.replace(/[-_]+/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).slice(0, 100))
    }
    setUploadResult(null)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('title', title || selectedFile.name)

    try {
      const result = await uploadDocument(formData)
      if (result) {
        setUploadResult(result)
      }
    } finally {
      setUploading(false)
    }
  }

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold text-text-primary">Upload Paper</h1>
        <p className="text-text-secondary mt-1">Add an academic PDF to start asking questions</p>
      </div>

      {/* Success state */}
      {uploadResult ? (
        <div className="animate-fade-in">
          <div className="bg-success/10 border border-success/20 rounded-xl p-8 text-center mb-6">
            <CheckCircle2 className="w-14 h-14 text-success mx-auto mb-4" />
            <h2 className="font-serif text-xl font-bold text-text-primary mb-2">Upload Successful!</h2>
            <p className="text-text-secondary">Your paper has been processed and is ready for Q&A.</p>
          </div>

          <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
            <h3 className="font-medium text-text-primary mb-4">Processing Results</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-bg-secondary rounded-lg p-4 text-center">
                <p className="text-2xl font-bold font-mono text-accent-primary">
                  {uploadResult.processing?.total_pages || uploadResult.document?.total_pages || '—'}
                </p>
                <p className="text-xs text-text-muted mt-1">Pages</p>
              </div>
              <div className="bg-bg-secondary rounded-lg p-4 text-center">
                <p className="text-2xl font-bold font-mono text-accent-secondary">
                  {uploadResult.processing?.total_chunks || uploadResult.document?.total_chunks || '—'}
                </p>
                <p className="text-xs text-text-muted mt-1">Chunks</p>
              </div>
              <div className="bg-bg-secondary rounded-lg p-4 text-center">
                <p className="text-2xl font-bold font-mono text-text-primary">
                  {uploadResult.document?.status || 'ready'}
                </p>
                <p className="text-xs text-text-muted mt-1">Status</p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/documents/${uploadResult.document?.id}`)}
              className="flex-1 flex items-center justify-center gap-2 py-3 bg-accent-primary text-bg-primary font-semibold rounded-lg hover:bg-accent-primary/90 transition-all"
            >
              Open Paper
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setSelectedFile(null)
                setTitle('')
                setUploadResult(null)
              }}
              className="px-6 py-3 bg-bg-secondary text-text-secondary font-medium rounded-lg hover:bg-bg-hover transition-all"
            >
              Upload Another
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
              ${dragOver
                ? 'border-accent-primary bg-accent-primary/5'
                : 'border-border hover:border-accent-primary/40 hover:bg-bg-card/50'
              }
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.tex"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files[0])}
            />

            {selectedFile ? (
              <div className="animate-fade-in">
                <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-accent-primary" />
                </div>
                <p className="font-medium text-text-primary mb-1">{selectedFile.name}</p>
                <p className="text-sm text-text-muted">{formatSize(selectedFile.size)}</p>
                <button
                  onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setTitle('') }}
                  className="mt-3 text-xs text-error hover:text-error/80 flex items-center gap-1 mx-auto"
                >
                  <X className="w-3 h-3" />
                  Remove
                </button>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-8 h-8 text-accent-primary/60" />
                </div>
                <p className="font-medium text-text-primary mb-1">
                  Drop your PDF here
                </p>
                <p className="text-sm text-text-muted mb-3">
                  or click to browse — max 50MB
                </p>
                <span className="inline-flex items-center gap-1 text-xs text-text-muted">
                  <Info className="w-3 h-3" />
                  Academic papers, research papers, dissertations, LaTeX source (.tex)
                </span>
              </>
            )}
          </div>

          {/* Title */}
          {selectedFile && (
            <div className="animate-fade-in">
              <label className="block text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">
                Document Title (optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-3 bg-bg-card border border-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-all"
                placeholder="Enter a title for this paper"
              />
              <p className="text-xs text-text-muted mt-1.5">
                The filename will be used if left empty
              </p>
            </div>
          )}

          {error && (
            <div className="p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Upload Button */}
          {selectedFile && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-3.5 bg-accent-primary text-bg-primary font-semibold rounded-lg hover:bg-accent-primary/90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading & Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload & Process Paper
                </>
              )}
            </button>
          )}

          {/* Info */}
          <div className="bg-bg-card border border-border rounded-xl p-5">
            <h3 className="font-medium text-text-primary mb-3 flex items-center gap-2">
              <Info className="w-4 h-4 text-accent-primary" />
              What happens next?
            </h3>
            <div className="space-y-2 text-sm text-text-secondary">
              <div className="flex gap-3">
                <span className="text-accent-primary font-mono text-xs mt-0.5">01</span>
                <p>Your PDF or LaTeX file is uploaded securely and stored on the server.</p>
              </div>
              <div className="flex gap-3">
                <span className="text-accent-primary font-mono text-xs mt-0.5">02</span>
                <p>Text is extracted and split into overlapping chunks (800 tokens each).</p>
              </div>
              <div className="flex gap-3">
                <span className="text-accent-primary font-mono text-xs mt-0.5">03</span>
                <p>Each chunk is embedded using OpenAI's embedding model and stored in PostgreSQL.</p>
              </div>
              <div className="flex gap-3">
                <span className="text-accent-primary font-mono text-xs mt-0.5">04</span>
                <p>Your paper is ready for citation-grounded Q&A!</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
