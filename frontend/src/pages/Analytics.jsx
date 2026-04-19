import React, { useEffect, useState } from 'react'
import { analyticsAPI } from '../api/client'
import {
  TrendingUp, DollarSign, Clock, Zap, CheckCircle2,
  AlertCircle, BarChart2, Activity, BookOpen,
  RefreshCw, Loader2
} from 'lucide-react'

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, color = 'bg-accent-primary/10 text-accent-primary', loading }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-5 hover:border-accent-primary/30 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
        {loading ? (
          <Loader2 className="w-5 h-5 text-text-muted animate-spin" />
        ) : (
          <span className="text-2xl font-bold font-mono text-text-primary">{value ?? '—'}</span>
        )}
      </div>
      <p className="text-sm font-medium text-text-primary">{label}</p>
      {sub && <p className="text-xs text-text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

// ─── Section Card ────────────────────────────────────────────────────────────

function SectionCard({ title, icon: Icon, children, actions }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <Icon className="w-4 h-4 text-accent-primary" />
          </div>
          <h2 className="font-semibold text-text-primary">{title}</h2>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className="p-6">{children}</div>
    </div>
  )
}

// ─── Simple Bar ─────────────────────────────────────────────────────────────

function SimpleBar({ value, max, color = 'bg-accent-primary' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="w-full bg-border rounded-full h-2 overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  )
}

// ─── Period Selector ──────────────────────────────────────────────────────────

function PeriodSelector({ value, onChange }) {
  const options = [
    { label: '7 days', value: 7 },
    { label: '30 days', value: 30 },
    { label: '90 days', value: 90 },
  ]
  return (
    <div className="flex items-center gap-1 bg-bg-secondary rounded-lg p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
            value === opt.value
              ? 'bg-accent-primary text-white'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ─── Model Performance Row ────────────────────────────────────────────────────

function ModelRow({ model }) {
  const successRate = model.success_rate ?? 0
  const providerColor = {
    codex: 'bg-blue-500',
    openai: 'bg-green-500',
    anthropic: 'bg-orange-500',
    google: 'bg-yellow-500',
  }[model.model_provider] || 'bg-gray-500'

  return (
    <tr className="border-b border-border/50 hover:bg-bg-secondary/50 transition-colors">
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${providerColor}`} />
          <span className="text-sm font-mono text-text-primary">{model.model_name}</span>
        </div>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="text-sm font-mono text-text-secondary">{model.call_count}</span>
      </td>
      <td className="py-3 px-4 text-center">
        <div className="flex items-center gap-2 justify-center">
          <span className="text-sm font-mono text-text-secondary">{successRate}%</span>
          <div className="w-16">
            <SimpleBar value={successRate} max={100} color={successRate > 80 ? 'bg-success' : successRate > 50 ? 'bg-accent-primary' : 'bg-error'} />
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="text-sm font-mono text-text-secondary">{model.avg_latency_ms}ms</span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="text-sm font-mono text-text-secondary">{model.max_latency_ms}ms</span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="text-sm font-mono text-text-secondary">{model.avg_answer_chars} chars</span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          model.failed_calls > 0 ? 'bg-error/10 text-error' : 'bg-success/10 text-success'
        }`}>
          {model.failed_calls}
        </span>
      </td>
    </tr>
  )
}

// ─── Cost Breakdown Row ───────────────────────────────────────────────────────

function CostRow({ item, maxCost }) {
  return (
    <div className="flex items-center gap-4 py-2">
      <div className="w-24 flex-shrink-0">
        <p className="text-xs font-medium text-text-primary capitalize">{item.api_provider}</p>
        <p className="text-xs text-text-muted capitalize">{item.cost_type}</p>
      </div>
      <div className="flex-1">
        <SimpleBar value={item.total_cost} max={maxCost} color="bg-accent-primary" />
      </div>
      <div className="w-44 flex-shrink-0 text-right">
        <p className="text-sm font-mono text-text-primary">${item.total_cost.toFixed(6)}</p>
        <p className="text-xs text-text-muted font-mono">{item.total_tokens.toLocaleString()} tokens</p>
      </div>
    </div>
  )
}

// ─── Phase Timing Bar ────────────────────────────────────────────────────────

function PhaseBar({ phase, avgMs, maxMs, totalMs }) {
  const pct = totalMs > 0 ? (avgMs / totalMs) * 100 : 0
  const colors = {
    embedding: 'bg-blue-500',
    vector_search: 'bg-green-500',
    llm_calls: 'bg-accent-primary',
    voting: 'bg-orange-500',
    total: 'bg-text-secondary',
  }
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-28 flex-shrink-0">
        <p className="text-xs font-medium text-text-primary capitalize">{phase.replace('_', ' ')}</p>
        <p className="text-xs text-text-muted">avg: {avgMs}ms · max: {maxMs}ms</p>
      </div>
      <div className="flex-1">
        <div className="w-full bg-border rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full ${colors[phase] || 'bg-accent-primary'} transition-all duration-700`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
      </div>
      <div className="w-16 flex-shrink-0 text-right">
        <span className="text-xs font-mono text-text-muted">{pct.toFixed(1)}%</span>
      </div>
    </div>
  )
}

// ─── Win Rate Row ────────────────────────────────────────────────────────────

function WinRateRow({ model }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
      <div className="flex-1">
        <p className="text-sm font-mono text-text-primary">{model.winning_model}</p>
        <p className="text-xs text-text-muted">
          {model.win_count} wins · {model.avg_citation_chunks} citations avg
        </p>
      </div>
      <div className="w-16 flex-shrink-0">
        <SimpleBar value={model.win_count} max={model.win_count} color="bg-accent-primary" />
      </div>
      <div className="w-10 flex-shrink-0 text-right">
        <span className="text-sm font-mono text-text-primary">{model.win_count}</span>
      </div>
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function Analytics() {
  const [period, setPeriod] = useState(30)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [data, setData] = useState({
    overview: null,
    cost: null,
    models: null,
    processing: null,
    timeline: null,
    voting: null,
  })

  const loadAll = async (days) => {
    setLoading(true)
    try {
      const [overview, cost, models, processing, timeline, voting] = await Promise.all([
        analyticsAPI.getOverview(days),
        analyticsAPI.getCost(days),
        analyticsAPI.getModelPerformance(days),
        analyticsAPI.getProcessing(days),
        analyticsAPI.getQueryTimeline(days),
        analyticsAPI.getVoting(days),
      ])
      setData({ overview, cost, models, processing, timeline, voting })
    } catch (err) {
      console.error('Analytics load failed:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll(period) }, [period])

  const handleRefresh = () => {
    setRefreshing(true)
    loadAll(period).finally(() => setRefreshing(false))
  }

  const o = data.overview?.data || {}
  const cost = data.cost?.data || {}
  const models = data.models?.data || {}
  const proc = data.processing?.data || {}
  const tl = data.timeline?.data || {}
  const vt = data.voting?.data || {}

  const maxCost = cost.by_provider?.length
    ? Math.max(...cost.by_provider.map(p => p.total_cost), 0.0001)
    : 0.0001

  const totalPhaseMs = tl.aggregates?.find(p => p.phase === 'total')?.avg_ms || 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
          <p className="text-sm text-text-muted mt-1">
            Usage stats, costs, and model performance — last {o.period_days || period} days
          </p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodSelector value={period} onChange={(p) => setPeriod(p)} />
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-card border border-border text-sm text-text-secondary hover:text-text-primary hover:border-accent-primary/30 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BookOpen} label="Documents Uploaded"
          value={o.total_uploads} sub={`in last ${o.period_days || period} days`}
          color="bg-accent-primary/10 text-accent-primary" loading={loading} />
        <StatCard icon={Activity} label="LLM Calls"
          value={o.total_queries}
          sub={`${o.successful_llm_calls || 0} ok · ${o.failed_llm_calls || 0} failed`}
          color="bg-blue-500/10 text-blue-500" loading={loading} />
        <StatCard icon={DollarSign} label="Est. API Cost"
          value={o.total_cost_usd != null ? `$${o.total_cost_usd.toFixed(4)}` : '$0.0000'}
          sub="across all providers" color="bg-green-500/10 text-green-500" loading={loading} />
        <StatCard icon={Clock} label="Avg LLM Latency"
          value={o.avg_llm_latency_ms ? `${o.avg_llm_latency_ms}ms` : '—'}
          sub="for successful calls" color="bg-orange-500/10 text-orange-500" loading={loading} />
      </div>

      {/* Model Performance Table */}
      <SectionCard title="Model Performance" icon={Zap} actions={
        <span className="text-xs text-text-muted font-mono">{models.models?.length || 0} models</span>
      }>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : models.models?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  {['Model', 'Calls', 'Success Rate', 'Avg Latency', 'Max Latency', 'Avg Output', 'Failed'].map(h => (
                    <th key={h} className={`text-xs font-medium text-text-muted uppercase tracking-wider pb-3 ${h === 'Model' ? 'text-left' : 'text-center'} ${h === 'Model' ? 'px-4' : 'px-2'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.models.map((m, i) => <ModelRow key={i} model={m} />)}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-text-muted text-center py-10">No model call data yet. Ask some questions!</p>
        )}
      </SectionCard>

      {/* Cost + Timeline side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SectionCard title="API Cost Breakdown" icon={DollarSign}>
          {loading ? (
            <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-text-muted animate-spin" /></div>
          ) : cost.by_provider?.length > 0 ? (
            <div>
              {cost.by_provider.map((item, i) => <CostRow key={i} item={item} maxCost={maxCost} />)}
              {cost.by_model?.length > 0 && (
                <div className="border-t border-border mt-4 pt-3">
                  <p className="text-xs text-text-muted mb-2 uppercase tracking-wider font-medium">By Model</p>
                  {cost.by_model.map((m, i) => (
                    <div key={i} className="flex justify-between items-center py-1">
                      <span className="text-xs font-mono text-text-secondary">{m.model_name}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-text-muted font-mono">{m.call_count} calls</span>
                        <span className="text-xs font-mono text-text-primary">${m.total_cost.toFixed(6)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-10">No cost data yet.</p>
          )}
        </SectionCard>

        <SectionCard title="Query Pipeline Timing" icon={Clock}>
          {loading ? (
            <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-text-muted animate-spin" /></div>
          ) : tl.aggregates?.length > 0 ? (
            <div className="space-y-1">
              {tl.aggregates.map((p, i) => (
                <PhaseBar key={i} phase={p.phase} avgMs={p.avg_ms} maxMs={p.max_ms} totalMs={totalPhaseMs} />
              ))}
              <p className="text-xs text-text-muted mt-3">
                Total = embedding + vector_search + llm_calls + voting
              </p>
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-10">No query timing data yet.</p>
          )}
        </SectionCard>
      </div>

      {/* Processing + Voting side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SectionCard title="Document Processing" icon={BookOpen}>
          {loading ? (
            <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-text-muted animate-spin" /></div>
          ) : (
            <div className="space-y-4">
              {proc.by_file_type?.length > 0 ? (
                <div className="space-y-3">
                  {proc.by_file_type.map((t, i) => (
                    <div key={i} className="bg-bg-secondary rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-mono font-medium text-text-primary uppercase">.{t.file_type}</span>
                        <span className="text-xs text-text-muted">{t.count} uploads</span>
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-center">
                        {[
                          [t.avg_pages, 'avg pages'],
                          [t.avg_chunks, 'avg chunks'],
                          [t.avg_extraction_ms?.toFixed(0) + 'ms', 'extract'],
                          [t.avg_total_ms?.toFixed(0) + 'ms', 'total'],
                        ].map(([v, l], j) => (
                          <div key={j}>
                            <p className="text-xs font-mono text-text-primary">{v}</p>
                            <p className="text-xs text-text-muted">{l}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-muted text-center py-4">No processing data yet.</p>
              )}
              {proc.errors?.length > 0 && (
                <div className="border-t border-border pt-3">
                  <p className="text-xs text-error font-medium mb-2">Errors ({proc.errors.length})</p>
                  {proc.errors.map((e, i) => (
                    <div key={i} className="flex items-center gap-2 py-1">
                      <AlertCircle className="w-3 h-3 text-error flex-shrink-0" />
                      <span className="text-xs text-text-secondary">{e.error_stage}: {e.error_message}</span>
                      <span className="text-xs text-text-muted ml-auto">{e.count}x</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Answer Quality & Voting" icon={TrendingUp}>
          {loading ? (
            <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-text-muted animate-spin" /></div>
          ) : (
            <div className="space-y-4">
              {vt.win_rates?.length > 0 && (
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider font-medium mb-3">Win Rate by Model</p>
                  {vt.win_rates.map((m, i) => <WinRateRow key={i} model={m} />)}
                </div>
              )}
              {vt.agreement_distribution?.length > 0 && (
                <div className="border-t border-border pt-3">
                  <p className="text-xs text-text-muted uppercase tracking-wider font-medium mb-3">Agreement Score Distribution</p>
                  {vt.agreement_distribution.map((d, i) => (
                    <div key={i} className="flex items-center gap-3 py-1.5">
                      <span className="text-xs font-mono text-text-secondary w-20">{d.bucket}</span>
                      <div className="flex-1">
                        <SimpleBar value={d.count} max={Math.max(...vt.agreement_distribution.map(x => x.count), 1)} color="bg-accent-primary" />
                      </div>
                      <span className="text-xs font-mono text-text-muted w-8 text-right">{d.count}</span>
                    </div>
                  ))}
                </div>
              )}
              {!vt.win_rates?.length && !vt.agreement_distribution?.length && (
                <p className="text-sm text-text-muted text-center py-4">No voting data yet.</p>
              )}
            </div>
          )}
        </SectionCard>
      </div>

      {/* Daily Cost Trend */}
      {cost.daily?.length > 0 && (
        <SectionCard title="Daily Cost Trend" icon={BarChart2}>
          <div className="space-y-1">
            {cost.daily.map((d, i) => (
              <div key={i} className="flex items-center gap-4 py-1.5 border-b border-border/30 last:border-0">
                <span className="text-xs font-mono text-text-muted w-28 flex-shrink-0">{d.date}</span>
                <div className="flex-1">
                  <SimpleBar value={d.cost} max={Math.max(...cost.daily.map(x => x.cost), 0.0001)} color="bg-accent-primary" />
                </div>
                <div className="flex items-center gap-4 w-48 flex-shrink-0">
                  <span className="text-xs font-mono text-text-primary">${d.cost.toFixed(6)}</span>
                  <span className="text-xs text-text-muted font-mono">{d.tokens.toLocaleString()} tok</span>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  )
}
