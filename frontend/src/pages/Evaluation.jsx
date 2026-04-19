import React, { useEffect, useState } from 'react'
import { useQAStore } from '../store'
import {
  BarChart3, TrendingUp, Clock, Brain, Award,
  Target, Zap, Loader2
} from 'lucide-react'

function MetricCard({ icon: Icon, label, value, sub, color, delay = 0 }) {
  return (
    <div
      className="bg-bg-card border border-border rounded-xl p-5 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-3xl font-bold font-mono text-text-primary mb-1">{value}</p>
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      {sub && <p className="text-xs text-text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

export default function Evaluation() {
  const { metrics, fetchMetrics } = useQAStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics().then(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
      </div>
    )
  }

  const modelEntries = metrics?.model_win_counts
    ? Object.entries(metrics.model_win_counts).sort((a, b) => b[1] - a[1])
    : []
  const totalWins = modelEntries.reduce((sum, [, w]) => sum + w, 0)

  const avgLatency = metrics?.avg_latency_by_model
    ? Object.values(metrics.avg_latency_by_model).reduce((a, b) => a + b, 0) / Object.keys(metrics.avg_latency_by_model).length
    : 0

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold text-text-primary">Evaluation Dashboard</h1>
        <p className="text-text-secondary mt-1">
          Multi-model performance metrics and citation-grounded analysis
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard
          icon={Brain}
          label="Total Questions"
          value={metrics?.total_queries || 0}
          sub="QA sessions analyzed"
          color="bg-accent-primary/10 text-accent-primary"
          delay={0}
        />
        <MetricCard
          icon={TrendingUp}
          label="Agreement Score"
          value={metrics?.avg_agreement_score
            ? (metrics.avg_agreement_score * 100).toFixed(1) + '%'
            : '—'}
          sub="cross-model similarity"
          color="bg-accent-secondary/10 text-accent-secondary"
          delay={100}
        />
        <MetricCard
          icon={Target}
          label="Citation Overlap"
          value={metrics?.avg_citation_overlap
            ? (metrics.avg_citation_overlap * 100).toFixed(1) + '%'
            : '—'}
          sub="mutual citation Jaccard"
          color="bg-purple-500/10 text-purple-400"
          delay={200}
        />
        <MetricCard
          icon={Zap}
          label="Avg Latency"
          value={avgLatency > 0 ? (avgLatency / 1000).toFixed(1) + 's' : '—'}
          sub="across all models"
          color="bg-orange-500/10 text-orange-400"
          delay={300}
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Model Win Distribution */}
        <div className="bg-bg-card border border-border rounded-xl p-6 animate-fade-in" style={{ animationDelay: '400ms' }}>
          <h3 className="font-serif font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Award className="w-5 h-5 text-accent-primary" />
            Model Win Distribution
          </h3>

          {modelEntries.length === 0 ? (
            <div className="text-center py-8">
              <Brain className="w-10 h-10 text-text-muted/30 mx-auto mb-3" />
              <p className="text-sm text-text-muted">No data yet. Ask some questions first!</p>
            </div>
          ) : (
            <div className="space-y-5">
              {modelEntries.map(([model, wins], index) => {
                const pct = totalWins > 0 ? (wins / totalWins * 100) : 0
                const colors = [
                  'from-accent-primary to-accent-primary/70',
                  'from-accent-secondary to-accent-secondary/70',
                  'from-purple-500 to-purple-400',
                ]
                return (
                  <div key={model}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-text-muted">#{index + 1}</span>
                        <span className="text-sm font-medium text-text-primary">{model}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-mono text-text-primary">{wins} wins</span>
                        <span className="text-xs text-text-muted ml-2">({pct.toFixed(1)}%)</span>
                      </div>
                    </div>
                    <div className="h-3 bg-bg-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${colors[index % colors.length]} rounded-full transition-all duration-700`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Latency Comparison */}
        <div className="bg-bg-card border border-border rounded-xl p-6 animate-fade-in" style={{ animationDelay: '500ms' }}>
          <h3 className="font-serif font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-accent-secondary" />
            Response Latency by Model
          </h3>

          {metrics?.avg_latency_by_model && Object.keys(metrics.avg_latency_by_model).length > 0 ? (
            <div className="space-y-4">
              {Object.entries(metrics.avg_latency_by_model)
                .sort((a, b) => a[1] - b[1])
                .map(([model, latency], index) => {
                  const maxLatency = Math.max(...Object.values(metrics.avg_latency_by_model))
                  const pct = maxLatency > 0 ? (latency / maxLatency * 100) : 0
                  return (
                    <div key={model} className="flex items-center gap-3">
                      <span className="text-xs font-mono text-text-muted w-8">{index + 1}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm text-text-secondary">{model}</span>
                          <span className="text-xs font-mono text-text-primary">{(latency / 1000).toFixed(2)}s</span>
                        </div>
                        <div className="h-2 bg-bg-secondary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-secondary rounded-full transition-all duration-700"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  )
                })}
            </div>
          ) : (
            <div className="text-center py-8">
              <Clock className="w-10 h-10 text-text-muted/30 mx-auto mb-3" />
              <p className="text-sm text-text-muted">No latency data available yet</p>
            </div>
          )}
        </div>

        {/* Recent Sessions */}
        <div className="lg:col-span-2 bg-bg-card border border-border rounded-xl p-6 animate-fade-in" style={{ animationDelay: '600ms' }}>
          <h3 className="font-serif font-semibold text-text-primary mb-6 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent-primary" />
            Recent Query Sessions
          </h3>

          {metrics?.recent_sessions && metrics.recent_sessions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left text-xs font-medium text-text-muted pb-3">Query</th>
                    <th className="text-left text-xs font-medium text-text-muted pb-3">Model</th>
                    <th className="text-right text-xs font-medium text-text-muted pb-3">Agreement</th>
                    <th className="text-right text-xs font-medium text-text-muted pb-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {metrics.recent_sessions.map(session => (
                    <tr key={session.id} className="hover:bg-bg-hover/50 transition-colors">
                      <td className="py-3 text-sm text-text-secondary truncate max-w-md">
                        {session.query_text}
                      </td>
                      <td className="py-3 text-sm font-mono text-text-secondary">
                        {session.winning_model?.split('/')[1] || session.winning_model || '—'}
                      </td>
                      <td className="py-3 text-right">
                        {session.agreement_score != null ? (
                          <span className={`text-sm font-mono ${
                            session.agreement_score > 0.7 ? 'text-success' :
                            session.agreement_score > 0.4 ? 'text-accent-primary' : 'text-error'
                          }`}>
                            {(session.agreement_score * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-sm text-text-muted">—</span>
                        )}
                      </td>
                      <td className="py-3 text-right text-xs text-text-muted">
                        {new Date(session.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <BarChart3 className="w-10 h-10 text-text-muted/30 mx-auto mb-3" />
              <p className="text-sm text-text-muted">No sessions recorded yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
