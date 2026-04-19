import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useDocumentsStore, useQAStore } from '../store'
import { queriesAPI } from '../api/client'
import {
  ArrowLeft, Brain, FileText, Loader2, Send,
  Quote, ChevronDown, ChevronUp, CheckCircle2, AlertCircle,
  BookOpen, MessageSquare, Sparkles, BarChart3, Clock, History, X
} from 'lucide-react'
import AnswerWithCitations from '../components/AnswerWithCitations'

function getModelLabel(modelName) {
  if (!modelName) return '?'
  const parts = modelName.split('/')
  return parts[parts.length - 1]
}

function HistoryItem({ session, onLoad, isActive }) {
  const [expanded, setExpanded] = useState(false)
  const hasAnswer = session.final_answer?.answer_text

  return (
    <div className={`border rounded-lg overflow-hidden transition-all ${isActive ? 'border-accent-primary/50 bg-accent-primary/5' : 'border-border hover:border-border-hover'}`}>
      <button
        onClick={() => hasAnswer && setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 hover:bg-bg-hover transition-colors text-left"
      >
        <History className="w-4 h-4 text-text-muted flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-text-primary line-clamp-1">{session.query_text}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-text-muted">
              {session.final_answer?.winning_model ? (
                <span className="font-mono text-accent-secondary">{getModelLabel(session.final_answer.winning_model)}</span>
              ) : 'no answer'}
            </span>
            {session.created_at && (
              <>
                <span className="text-text-muted/30">·</span>
                <span className="text-xs text-text-muted">{new Date(session.created_at).toLocaleString()}</span>
              </>
            )}
          </div>
        </div>
        {hasAnswer && (
          <button
            onClick={(e) => { e.stopPropagation(); onLoad(session) }}
            className="flex-shrink-0 text-xs px-2 py-1 rounded bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors"
          >
            Load
          </button>
        )}
        {expanded ? <ChevronUp className="w-4 h-4 text-text-muted flex-shrink-0" /> : hasAnswer ? <ChevronDown className="w-4 h-4 text-text-muted flex-shrink-0" /> : null}
      </button>
      {expanded && hasAnswer && (
        <div className="px-3 pb-3 border-t border-border/50">
          <p className="pt-3 text-sm text-text-secondary leading-relaxed line-clamp-3">
            {session.final_answer.answer_text}
          </p>
        </div>
      )}
    </div>
  )
}

function ModelResultCard({ result, showScores, index }) {
  const [expanded, setExpanded] = useState(index === 0)

  const isSuccess = result.success
  const modelColors = {
    'openai': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    'anthropic': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    'google': 'bg-green-500/10 text-green-400 border-green-500/20',
    'codex': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    'claude': 'bg-red-500/10 text-red-400 border-red-500/20',
  }

  let colorClass = 'bg-text-muted/10 text-text-muted border-text-muted/20'
  for (const [key, val] of Object.entries(modelColors)) {
    if (result.model_name?.includes(key)) { colorClass = val; break }
  }

  return (
    <div className="border border-border rounded-xl overflow-hidden animate-fade-in" style={{ animationDelay: `${index * 100}ms` }}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono border ${colorClass}`}>
            {result.model_name?.split('/')[1] || result.model_name?.split('/')[0]}
          </span>
          {isSuccess ? (
            <CheckCircle2 className="w-4 h-4 text-success" />
          ) : (
            <AlertCircle className="w-4 h-4 text-error" />
          )}
          {result.latency_ms && (
            <span className="text-xs text-text-muted flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.latency_ms.toFixed(0)}ms
            </span>
          )}
          {result.tokens_used > 0 && (
            <span className="text-xs text-text-muted font-mono">{result.tokens_used} tok</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {showScores && showScores[result.model_name] && (
            <span className="text-xs font-mono text-accent-primary">
              {(showScores[result.model_name].combined_score * 100).toFixed(0)}%
            </span>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-border">
          <div className="pt-4">
            {isSuccess ? (
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {result.answer_text}
              </p>
            ) : (
              <p className="text-sm text-error">{result.answer_text}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CitationCard({ citation, index }) {
  const [expanded, setExpanded] = useState(index < 3)
  const isHighlighted = false

  return (
    <div
      id={`citation-${citation.id}`}
      className={`border border-border rounded-lg overflow-hidden transition-all ${isHighlighted ? 'ring-2 ring-accent-primary rounded-lg' : ''}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded bg-accent-primary/15 text-accent-primary text-xs font-mono font-bold flex-shrink-0">
            {citation.number}
          </span>
          <Quote className="w-3.5 h-3.5 text-accent-primary flex-shrink-0" />
          <span className="text-xs font-medium text-text-secondary">
            Page {citation.page_number}
          </span>
          {index < 3 && <span className="text-xs bg-accent-primary/10 text-accent-primary px-1.5 py-0.5 rounded">Top Citation</span>}
        </div>
        {expanded ? <ChevronUp className="w-3.5 h-3.5 text-text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-text-muted" />}
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-border/50">
          {citation.first_sentence && (
            <p className="pt-3 text-sm text-accent-secondary leading-relaxed italic border-l-2 border-accent-primary/30 pl-3 mb-3">
              {citation.first_sentence}
            </p>
          )}
          <p className="text-xs text-text-secondary leading-relaxed font-mono">
            {citation.text}
          </p>
        </div>
      )}
    </div>
  )
}

export default function DocumentView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getDocument, currentDocument, fetchChunks, chunks } = useDocumentsStore()
  const { askQuestion, summarize, currentResult, loading, error, docHistory, fetchHistory, clearDocHistory } = useQAStore()

  const [question, setQuestion] = useState('')
  const [activeTab, setActiveTab] = useState('qa')
  const [summaryType, setSummaryType] = useState('abstract')
  const [showRetrieved, setShowRetrieved] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(null)

  useEffect(() => {
    getDocument(id)
    fetchChunks(id, { per_page: 20 })
    // Load Q&A history for this document
    fetchHistory({ document_id: id, per_page: 20 })
    return () => clearDocHistory()
  }, [id])

  const handleAskQuestion = async (e) => {
    e.preventDefault()
    if (!question.trim()) return
    const result = await askQuestion(id, question.trim())
    if (result?.query_session_id) {
      // Prepend new session to docHistory immediately so it shows in the list
      fetchHistory({ document_id: id, per_page: 1 }).then((data) => {
        if (data?.sessions?.length > 0) {
          const newSession = data.sessions[0]
          useQAStore.setState((state) => {
            const exists = state.docHistory.some((s) => s.id === newSession.id)
            if (!exists) return { docHistory: [newSession, ...state.docHistory] }
            return {}
          })
        }
      })
    }
  }

  const handleLoadHistory = async (session) => {
    setActiveSessionId(session.id)
    try {
      const res = await queriesAPI.getResult(session.id)
      const data = res.data
      // Synthesize a response shape matching what askQuestion returns
      const result = {
        query_session_id: session.id,
        question: session.query_text,
        final_answer: data.final_answer,
        citation_map: {},
        citations: (data.citation_chunks || []).map((c, i) => ({
          id: c.id,
          number: i + 1,
          page_number: c.page_number,
          text: c.text,
        })),
        model_results: (data.llm_results || []).map((r) => ({
          model_name: r.model_name,
          answer_text: r.answer_text,
          latency_ms: r.latency_ms,
          tokens_used: r.tokens_used,
          success: !r.answer_text?.startsWith('Error:'),
        })),
      }
      useQAStore.setState({ currentResult: result })
    } catch {
      // Silently fail — user can still see the session in the list
    }
  }

  const handleSummarize = async () => {
    await summarize(id, summaryType)
    setActiveTab('summary')
    // Refresh doc history so the summary session appears in the list
    fetchHistory({ document_id: id, per_page: 1 }).then((data) => {
      if (data?.sessions?.length > 0) {
        const newSession = data.sessions[0]
        useQAStore.setState((state) => {
          const exists = state.docHistory.some((s) => s.id === newSession.id)
          if (!exists) return { docHistory: [newSession, ...state.docHistory] }
          return {}
        })
      }
    })
  }

  if (!currentDocument) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
      </div>
    )
  }

  const statusBadge = {
    ready: 'bg-success/10 text-success border-success/20',
    processing: 'bg-accent-primary/10 text-accent-primary border-accent-primary/20',
    pending: 'bg-text-muted/10 text-text-muted border-text-muted/20',
    error: 'bg-error/10 text-error border-error/20',
  }[currentDocument.status] || ''

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-text-muted hover:text-text-primary transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="font-serif text-lg font-bold text-text-primary truncate">
            {currentDocument.title}
          </h1>
          <p className="text-xs text-text-muted truncate">{currentDocument.filename}</p>
        </div>
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border ${statusBadge}`}>
          {currentDocument.status}
        </span>
        <div className="text-right">
          <p className="text-xs text-text-muted">{currentDocument.total_pages} pages</p>
          <p className="text-xs text-text-muted">{currentDocument.total_chunks} chunks</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 border-b border-border flex gap-1">
        {[
          { id: 'qa', icon: MessageSquare, label: 'Q&A' },
          { id: 'summary', icon: BookOpen, label: 'Summary' },
          { id: 'chunks', icon: FileText, label: 'Chunks' },
        ].map(({ id: tabId, icon: Icon, label }) => (
          <button
            key={tabId}
            onClick={() => setActiveTab(tabId)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === tabId
                ? 'border-accent-primary text-accent-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'qa' && (
          <div className="p-6 max-w-4xl mx-auto">
            {/* Ask Question */}
            <form onSubmit={handleAskQuestion} className="mb-8">
              <label className="block text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">
                Ask a Question
              </label>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What is the main contribution of this paper?"
                  className="flex-1 px-4 py-3 bg-bg-card border border-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-all"
                  disabled={loading || currentDocument.status !== 'ready'}
                />
                <button
                  type="submit"
                  disabled={loading || !question.trim() || currentDocument.status !== 'ready'}
                  className="px-6 py-3 bg-accent-primary text-bg-primary font-semibold rounded-lg hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 whitespace-nowrap"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Ask AI
                </button>
              </div>
              {currentDocument.status !== 'ready' && (
                <p className="text-xs text-accent-primary mt-2">Document is being processed. Please wait...</p>
              )}
            </form>

            {/* Error */}
            {error && (
              <div className="mb-6 p-4 bg-error/10 border border-error/20 rounded-xl text-error text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* History Toggle */}
            {docHistory.length > 0 && (
              <div className="mb-6">
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors mb-3"
                >
                  <History className="w-4 h-4" />
                  Q&A History ({docHistory.length})
                  {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showHistory && (
                  <div className="space-y-2">
                    {docHistory.map((session) => (
                      <HistoryItem
                        key={session.id}
                        session={session}
                        onLoad={handleLoadHistory}
                        isActive={activeSessionId === session.id}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Results */}
            {currentResult && (
              <div className="space-y-6 animate-fade-in">
                {/* Final Answer */}
                {currentResult.final_answer && (
                  <div className="bg-bg-card border border-accent-primary/20 rounded-xl p-6 glow-amber">
                    <div className="flex items-center gap-2 mb-4">
                      <Sparkles className="w-4 h-4 text-accent-primary" />
                      <h3 className="font-medium text-accent-primary">Best Answer</h3>
                      <span className="ml-auto text-xs font-mono text-text-muted">
                        {currentResult.final_answer.winning_model?.split('/')[1]}
                      </span>
                    </div>
                    <AnswerWithCitations
                      text={currentResult.final_answer.answer_text}
                      citationMap={currentResult.citation_map}
                      onCitationClick={(id) => {
                        document.getElementById(`citation-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        document.getElementById(`citation-${id}`)?.classList.add('ring-2', 'ring-accent-primary', 'rounded-lg')
                        setTimeout(() => {
                          document.getElementById(`citation-${id}`)?.classList.remove('ring-2', 'ring-accent-primary', 'rounded-lg')
                        }, 2000)
                      }}
                    />

                    {/* Scores */}
                    {currentResult.voting_scores && Object.keys(currentResult.voting_scores).length > 1 && (
                      <div className="mt-4 pt-4 border-t border-border">
                        <p className="text-xs font-medium text-text-secondary mb-2">Model Agreement</p>
                        <div className="flex gap-4">
                          {Object.entries(currentResult.voting_scores).map(([model, scores]) => (
                            <div key={model} className="flex-1">
                              <div className="flex justify-between mb-1">
                                <span className="text-xs font-mono text-text-muted truncate">{model.split('/')[1]}</span>
                                <span className="text-xs font-mono text-accent-primary">{(scores.combined_score * 100).toFixed(0)}%</span>
                              </div>
                              <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary rounded-full"
                                  style={{ width: `${scores.combined_score * 100}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Citations */}
                {currentResult.citations && currentResult.citations.length > 0 && (
                  <div>
                    <h3 className="font-medium text-text-primary mb-3 flex items-center gap-2">
                      <Quote className="w-4 h-4 text-accent-primary" />
                      Supporting Citations ({currentResult.citations.length})
                    </h3>
                    <div className="space-y-2">
                      {currentResult.citations.map((c, i) => (
                        <CitationCard key={c.id || i} citation={c} index={i} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Model Comparison */}
                {currentResult.model_results && (
                  <div>
                    <h3 className="font-medium text-text-primary mb-3 flex items-center gap-2">
                      <Brain className="w-4 h-4 text-accent-secondary" />
                      All Model Responses
                    </h3>
                    <div className="space-y-2">
                      {currentResult.model_results.map((result, i) => (
                        <ModelResultCard
                          key={i}
                          result={result}
                          showScores={currentResult.voting_scores}
                          index={i}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Retrieved Chunks */}
                {currentResult.retrieved_chunks && (
                  <details className="border border-border rounded-xl">
                    <summary className="flex items-center justify-between p-4 cursor-pointer hover:bg-bg-hover">
                      <span className="text-sm font-medium text-text-secondary">
                        Retrieved Context ({currentResult.retrieved_chunks.length} chunks)
                      </span>
                      {showRetrieved ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
                    </summary>
                    <div className="px-4 pb-4 border-t border-border space-y-2">
                      {currentResult.retrieved_chunks.map((chunk, i) => (
                        <div key={chunk.id || i} className="pt-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-text-muted font-mono">
                              Chunk {chunk.id?.slice(0, 8)}... · Page {chunk.page_number}
                            </span>
                            <span className="text-xs font-mono text-accent-secondary">
                              {(chunk.similarity * 100).toFixed(1)}% match
                            </span>
                          </div>
                          <p className="text-xs text-text-secondary font-mono leading-relaxed">
                            {chunk.text_preview}
                          </p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="p-6 max-w-4xl mx-auto">
            <div className="mb-6 flex items-center gap-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Summary Type</label>
                <div className="flex gap-2">
                  {['abstract', 'full', 'section'].map(type => (
                    <button
                      key={type}
                      onClick={() => setSummaryType(type)}
                      className={`px-4 py-2 text-sm rounded-lg border transition-all ${
                        summaryType === type
                          ? 'bg-accent-primary/10 text-accent-primary border-accent-primary/30'
                          : 'bg-bg-card text-text-secondary border-border hover:border-accent-primary/30'
                      }`}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={handleSummarize}
                disabled={loading || currentDocument.status !== 'ready'}
                className="px-6 py-2 bg-accent-primary text-bg-primary font-semibold rounded-lg hover:bg-accent-primary/90 disabled:opacity-50 transition-all flex items-center gap-2 mt-5"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generate Summary
              </button>
            </div>

            {currentResult && currentResult.final_answer && (
              <div className="bg-bg-card border border-border rounded-xl p-6 animate-fade-in">
                <h3 className="font-serif font-semibold text-text-primary mb-4">
                  {summaryType.charAt(0).toUpperCase() + summaryType.slice(1)} Summary
                </h3>
                <p className="text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {currentResult.final_answer.answer_text}
                </p>

                {currentResult.model_results && (
                  <div className="mt-6 pt-6 border-t border-border">
                    <h4 className="text-sm font-medium text-text-secondary mb-3">Model Responses</h4>
                    <div className="space-y-2">
                      {currentResult.model_results.map((r, i) => (
                        <ModelResultCard key={i} result={r} showScores={currentResult.voting_scores} index={i} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'chunks' && (
          <div className="p-6 max-w-4xl mx-auto">
            <h2 className="font-serif text-lg font-semibold text-text-primary mb-4">
              Document Chunks ({chunks.length})
            </h2>
            <div className="space-y-3">
              {chunks.map((chunk, i) => (
                <div key={chunk.id} className="bg-bg-card border border-border rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-mono bg-accent-primary/10 text-accent-primary px-2 py-0.5 rounded">
                      Chunk {chunk.chunk_index}
                    </span>
                    <span className="text-xs text-text-muted">Page {chunk.page_number}</span>
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {chunk.text_preview || chunk.text?.slice(0, 300) + '...'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
