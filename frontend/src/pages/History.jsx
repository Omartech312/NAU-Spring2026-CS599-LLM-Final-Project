import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQAStore } from '../store'
import { queriesAPI } from '../api/client'
import {
  MessageSquare, BookOpen, Clock, ChevronRight,
  ArrowUpRight, Loader2, BarChart3
} from 'lucide-react'

function HistoryItem({ session }) {
  const iconMap = {
    qa: <MessageSquare className="w-4 h-4" />,
    summary: <BookOpen className="w-4 h-4" />,
  }

  const timeAgo = (date) => {
    const now = new Date()
    const d = new Date(date)
    const diff = (now - d) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  return (
    <Link
      to={`/documents/${session.document_id}`}
      className="block bg-bg-card border border-border rounded-xl p-4 hover:border-accent-primary/30 transition-all group"
    >
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          session.query_type === 'qa' ? 'bg-accent-primary/10 text-accent-primary' : 'bg-accent-secondary/10 text-accent-secondary'
        }`}>
          {iconMap[session.query_type] || <MessageSquare className="w-4 h-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary line-clamp-2 group-hover:text-accent-primary transition-colors">
            {session.query_text}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-text-muted flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {timeAgo(session.created_at)}
            </span>
            {session.final_answer && (
              <>
                <span className="text-xs text-text-muted">
                  {session.final_answer.winning_model?.split('/')[1] || session.final_answer.winning_model}
                </span>
                {session.final_answer.agreement_score > 0 && (
                  <span className="text-xs font-mono text-accent-primary">
                    {(session.final_answer.agreement_score * 100).toFixed(0)}% agree
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent-primary flex-shrink-0 mt-1" />
      </div>
    </Link>
  )
}

export default function History() {
  const { history, fetchHistory, loading } = useQAStore()
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    async function load() {
      const params = { page, per_page: 20 }
      if (filter !== 'all') params.query_type = filter
      const data = await fetchHistory(params)
      if (data) setTotalPages(data.pages)
    }
    load()
  }, [page, filter])

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-serif text-3xl font-bold text-text-primary">Query History</h1>
          <p className="text-text-secondary mt-1">All your questions and summaries</p>
        </div>
        <Link
          to="/evaluation"
          className="flex items-center gap-2 px-4 py-2 bg-bg-card border border-border rounded-lg text-sm text-text-secondary hover:text-text-primary hover:border-accent-primary/30 transition-all"
        >
          <BarChart3 className="w-4 h-4" />
          Evaluation
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {['all', 'qa', 'summary'].map(f => (
          <button
            key={f}
            onClick={() => { setFilter(f); setPage(1) }}
            className={`px-4 py-2 text-sm rounded-lg border transition-all ${
              filter === f
                ? 'bg-accent-primary/10 text-accent-primary border-accent-primary/30'
                : 'bg-bg-card text-text-secondary border-border hover:border-accent-primary/30'
            }`}
          >
            {f === 'all' ? 'All' : f === 'qa' ? 'Q&A' : 'Summaries'}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
        </div>
      ) : history.length === 0 ? (
        <div className="bg-bg-card border border-border border-dashed rounded-xl p-12 text-center">
          <MessageSquare className="w-12 h-12 text-text-muted/30 mx-auto mb-4" />
          <h3 className="font-medium text-text-primary mb-2">No queries yet</h3>
          <p className="text-sm text-text-muted">Upload a paper and ask your first question</p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map(session => (
            <HistoryItem key={session.id} session={session} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 text-sm bg-bg-card border border-border rounded-lg disabled:opacity-30 hover:border-accent-primary/30 transition-all"
          >
            Previous
          </button>
          <span className="text-sm text-text-muted px-3">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 text-sm bg-bg-card border border-border rounded-lg disabled:opacity-30 hover:border-accent-primary/30 transition-all"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
