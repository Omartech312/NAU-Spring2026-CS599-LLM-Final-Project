import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDocumentsStore, useQAStore, useAuthStore } from '../store'
import { documentsAPI, queriesAPI } from '../api/client'
import {
  FileText, Upload, Clock, TrendingUp, BookOpen,
  Sparkles, ChevronRight, Brain, CheckCircle2, AlertCircle
} from 'lucide-react'

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-5 hover:border-accent-primary/30 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <span className="text-2xl font-bold font-mono text-text-primary">{value}</span>
      </div>
      <p className="text-sm font-medium text-text-primary">{label}</p>
      {sub && <p className="text-xs text-text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

function DocumentCard({ doc }) {
  const statusColors = {
    ready: 'bg-success/10 text-success border-success/20',
    processing: 'bg-accent-primary/10 text-accent-primary border-accent-primary/20',
    pending: 'bg-text-muted/10 text-text-muted border-text-muted/20',
    error: 'bg-error/10 text-error border-error/20',
  }
  const statusIcons = {
    ready: <CheckCircle2 className="w-3 h-3" />,
    processing: <Clock className="w-3 h-3" />,
    pending: <Clock className="w-3 h-3" />,
    error: <AlertCircle className="w-3 h-3" />,
  }

  return (
    <Link
      to={`/documents/${doc.id}`}
      className="block bg-bg-card border border-border rounded-xl p-5 hover:border-accent-primary/40 transition-all group"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-primary/10 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-accent-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-text-primary group-hover:text-accent-primary transition-colors truncate">
            {doc.title}
          </h3>
          <p className="text-xs text-text-muted mt-0.5 truncate">{doc.filename}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${statusColors[doc.status] || statusColors.pending}`}>
              {statusIcons[doc.status]}
              {doc.status}
            </span>
            <span className="text-xs text-text-muted">{doc.total_pages} pages</span>
            <span className="text-xs text-text-muted">{doc.total_chunks} chunks</span>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent-primary transition-colors flex-shrink-0 mt-1" />
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { user } = useAuthStore()
  const { documents, fetchDocuments } = useDocumentsStore()
  const { metrics, fetchMetrics } = useQAStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      await fetchDocuments({ per_page: 100 })
      await fetchMetrics()
      setLoading(false)
    }
    load()
  }, [])

  const readyDocs = documents.filter(d => d.status === 'ready')
  const processingDocs = documents.filter(d => ['pending', 'processing'].includes(d.status))

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold text-text-primary">
          {greeting}, {user?.full_name?.split(' ')[0] || 'Researcher'}
        </h1>
        <p className="text-text-secondary mt-1">
          Upload academic papers and ask citation-grounded questions
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={BookOpen}
          label="Total Documents"
          value={documents.length}
          sub="uploaded papers"
          color="bg-accent-primary/10 text-accent-primary"
        />
        <StatCard
          icon={CheckCircle2}
          label="Processed"
          value={readyDocs.length}
          sub="ready for Q&A"
          color="bg-success/10 text-success"
        />
        <StatCard
          icon={Brain}
          label="Questions Asked"
          value={metrics?.total_queries || 0}
          sub="across all docs"
          color="bg-accent-secondary/10 text-accent-secondary"
        />
        <StatCard
          icon={TrendingUp}
          label="Agreement Score"
          value={metrics?.avg_agreement_score ? (metrics.avg_agreement_score * 100).toFixed(0) + '%' : '—'}
          sub="multi-model avg"
          color="bg-purple-500/10 text-purple-400"
        />
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Document List */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-semibold text-text-primary">Your Papers</h2>
            <Link
              to="/upload"
              className="flex items-center gap-1.5 text-sm text-accent-primary hover:text-accent-primary/80 font-medium"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-bg-card border border-border rounded-xl p-5 animate-pulse">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-bg-secondary" />
                    <div className="flex-1">
                      <div className="h-4 bg-bg-secondary rounded w-3/4 mb-2" />
                      <div className="h-3 bg-bg-secondary rounded w-1/2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="bg-bg-card border border-border border-dashed rounded-xl p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-accent-primary/40" />
              </div>
              <h3 className="font-medium text-text-primary mb-2">No papers yet</h3>
              <p className="text-sm text-text-muted mb-4">Upload your first academic paper to get started</p>
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-bg-primary font-medium rounded-lg hover:bg-accent-primary/90 transition-all"
              >
                <Upload className="w-4 h-4" />
                Upload Paper
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map(doc => (
                <DocumentCard key={doc.id} doc={doc} />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div>
          {/* Quick Start */}
          <div className="bg-bg-card border border-border rounded-xl p-5 mb-6">
            <h3 className="font-medium text-text-primary mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent-primary" />
              How It Works
            </h3>
            <div className="space-y-3">
              {[
                { step: '1', title: 'Upload PDF', desc: 'Add your academic paper' },
                { step: '2', title: 'Ask Questions', desc: 'Get answers with citations' },
                { step: '3', title: 'Compare Models', desc: 'See multi-LLM analysis' },
              ].map(({ step, title, desc }) => (
                <div key={step} className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-accent-primary/10 text-accent-primary text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                    {step}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{title}</p>
                    <p className="text-xs text-text-muted">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Performance */}
          {metrics?.model_win_counts && Object.keys(metrics.model_win_counts).length > 0 && (
            <div className="bg-bg-card border border-border rounded-xl p-5">
              <h3 className="font-medium text-text-primary mb-4">Model Performance</h3>
              <div className="space-y-3">
                {Object.entries(metrics.model_win_counts).map(([model, wins]) => {
                  const total = Object.values(metrics.model_win_counts).reduce((a, b) => a + b, 0)
                  const pct = total > 0 ? (wins / total * 100) : 0
                  return (
                    <div key={model}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-text-secondary truncate">{model}</span>
                        <span className="text-xs font-mono text-text-muted">{wins} wins ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary rounded-full transition-all duration-700"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
