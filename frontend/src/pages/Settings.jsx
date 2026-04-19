import React, { useEffect, useState } from 'react'
import { Copy, Check, Monitor, Globe, Zap, AlertCircle, Settings2, Terminal, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp, Download, RefreshCw } from 'lucide-react'

const SYSTEM_API = '/api/system'

function Field({ label, value, mono = false, copyable = false, hint }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</label>
      <div className="flex items-center gap-2">
        <div className={`flex-1 px-3 py-2 bg-bg-secondary rounded-lg border border-border text-sm ${mono ? 'font-mono text-text-primary' : 'text-text-secondary'}`}>
          {value || <span className="text-text-muted italic">not detected</span>}
        </div>
        {copyable && value && (
          <button
            onClick={handleCopy}
            className="flex-shrink-0 p-2 rounded-lg border border-border text-text-muted hover:text-accent-primary hover:border-accent-primary/30 transition-all"
            title="Copy"
          >
            {copied ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  )
}

function CliCard({ cli, onInstall, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [installing, setInstalling] = useState(false)
  const [installStatus, setInstallStatus] = useState(null)

  const cliKey = cli.name.toLowerCase().replace(' cli', '')

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setExpanded(true)
    try {
      const res = await fetch(`${SYSTEM_API}/cli-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cli: cliKey, question: 'What is 2+2?' }),
      })
      const data = await res.json()
      setTestResult(data)
    } catch (err) {
      setTestResult({ error: err.message, success: false })
    } finally {
      setTesting(false)
    }
  }

  const handleInstall = async () => {
    setInstalling(true)
    setInstallStatus(null)
    try {
      const res = await fetch(`${SYSTEM_API}/cli-install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cli: cliKey }),
      })
      const data = await res.json()
      setInstallStatus(data)

      if (data.status === 'installing' || data.status === 'already_installed') {
        let attempts = 0
        const poll = setInterval(async () => {
          attempts++
          const statusRes = await fetch(`${SYSTEM_API}/cli-status`)
          const statusData = await statusRes.json()
          const updated = statusData.clis?.find(
            (c) => c.name.toLowerCase() === cli.name.toLowerCase()
          )
          if (updated?.found || attempts >= 20) {
            clearInterval(poll)
            onRefresh()
          }
        }, 3000)
      }
    } catch (err) {
      setInstallStatus({ error: err.message })
    } finally {
      setInstalling(false)
    }
  }

  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${cli.found ? 'border-border hover:border-accent-primary/30' : 'border-border'}`}>
      <div className="flex items-center gap-3 p-4">
        {/* Status icon */}
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
          installing
            ? 'bg-accent-primary/10'
            : cli.found
            ? 'bg-success/10'
            : 'bg-error/10'
        }`}>
          {installing ? (
            <RefreshCw className="w-5 h-5 text-accent-primary animate-spin" />
          ) : cli.found ? (
            <CheckCircle2 className="w-5 h-5 text-success" />
          ) : (
            <XCircle className="w-5 h-5 text-error" />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-accent-secondary" />
            <span className="font-semibold text-text-primary">{cli.name}</span>
            {installing ? (
              <span className="text-xs font-mono bg-accent-primary/10 text-accent-primary px-1.5 py-0.5 rounded">
                installing…
              </span>
            ) : cli.found ? (
              <span className="text-xs font-mono bg-success/10 text-success px-1.5 py-0.5 rounded">
                {cli.version !== 'unknown' ? cli.version : 'detected'}
              </span>
            ) : (
              <span className="text-xs bg-error/10 text-error px-1.5 py-0.5 rounded">not found</span>
            )}
          </div>

          {/* Error from version check */}
          {cli.found && cli.error && (
            <p className="text-xs text-error mt-0.5">{cli.error}</p>
          )}

          {/* Install hint */}
          {!cli.found && !installing && cli.install_hint && (
            <code className="block mt-1 text-xs font-mono bg-bg-secondary px-2 py-1 rounded border border-border text-accent-secondary">
              {cli.install_hint}
            </code>
          )}

          {/* Install result */}
          {installStatus && !cli.found && (
            <div className={`mt-1.5 flex items-start gap-1.5 text-xs ${
              installStatus.error ? 'text-error' : 'text-success'
            }`}>
              {installStatus.error ? (
                <><XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-px" /> {installStatus.error}</>
              ) : (
                <><CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-px" /> {installStatus.message}</>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Install button */}
          {!cli.found && !installing && (
            <button
              onClick={handleInstall}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-all font-medium"
            >
              <Download className="w-3.5 h-3.5" />
              Install
            </button>
          )}
          {/* Test button */}
          {cli.found && (
            <button
              onClick={handleTest}
              disabled={testing}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 disabled:opacity-50 transition-all font-medium"
            >
              {testing ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Testing…</>
              ) : (
                'Test'
              )}
            </button>
          )}
          {testResult && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-text-muted hover:text-text-primary transition-colors"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Test result */}
      {expanded && testResult && (
        <div className="px-4 pb-4 border-t border-border/50 pt-3">
          {testResult.success ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-success">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Success
                </span>
                {testResult.model_name && (
                  <span className="font-mono text-text-muted">{testResult.model_name}</span>
                )}
                <span className="text-text-muted">{testResult.latency_ms}ms</span>
                {testResult.tokens_used > 0 && (
                  <span className="text-text-muted">{testResult.tokens_used} tok</span>
                )}
              </div>
              <p className="text-sm text-text-secondary leading-relaxed bg-bg-secondary rounded-lg p-3 font-mono">
                {testResult.answer_text || <span className="italic text-text-muted">empty response</span>}
              </p>
            </div>
          ) : (
            <div className="flex items-start gap-2 text-xs text-error">
              <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-px" />
              <span>{testResult.error || 'Test failed'}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Settings() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [cliStatus, setCliStatus] = useState(null)
  const [cliLoading, setCliLoading] = useState(true)

  useEffect(() => {
    fetchSystemInfo()
    fetchCliStatus()
  }, [])

  const fetchSystemInfo = () => {
    fetch(`${SYSTEM_API}/info`)
      .then((r) => r.json())
      .then((data) => setSystemInfo(data))
      .catch(() => {})
  }

  const fetchCliStatus = () => {
    setCliLoading(true)
    fetch(`${SYSTEM_API}/cli-status`)
      .then((r) => r.json())
      .then((data) => { setCliStatus(data); setCliLoading(false) })
      .catch(() => setCliLoading(false))
  }

  const localIp = systemInfo?.local_ip || '—'
  const hostname = systemInfo?.hostname || '—'
  const frontendUrl = systemInfo?.frontend_url || `http://${localIp}:3000`
  const backendUrl = systemInfo?.backend_url || `http://${localIp}:5001`

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-primary/10 flex items-center justify-center">
            <Settings2 className="w-5 h-5 text-accent-primary" />
          </div>
          Settings
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Configure your server URLs, LLM CLI tools, and connection options.
        </p>
      </div>

      {/* Server URLs */}
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <Globe className="w-4 h-4 text-accent-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-text-primary">Server URLs</h2>
            <p className="text-xs text-text-muted">Use these URLs to access CitationLLM from other devices.</p>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Auto-detected info */}
          <div className="bg-bg-secondary rounded-lg p-4 flex items-start gap-3">
            <Monitor className="w-4 h-4 text-accent-primary flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-text-primary mb-2">
                Machine: <span className="font-mono text-accent-primary">{hostname}</span>
              </p>
              <p className="text-xs font-medium text-text-primary mb-2">
                Auto-detected local IP: <span className="font-mono text-accent-primary">{localIp}</span>
              </p>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-text-muted w-20">Frontend:</span>
                  <span className="text-xs font-mono text-text-secondary">{frontendUrl}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-text-muted w-20">Backend:</span>
                  <span className="text-xs font-mono text-text-secondary">{backendUrl}</span>
                </div>
              </div>
              <p className="text-xs text-text-muted mt-2">
                Copy the URL above and paste it in your mobile device or another computer on the same network.
              </p>
            </div>
          </div>

          <Field
            label="Frontend URL"
            value={frontendUrl}
            mono
            copyable
            hint="Paste this URL in your mobile device or another computer on the same network."
          />

          <Field
            label="Backend API URL"
            value={backendUrl}
            mono
            copyable
            hint="The backend must be running for the app to work. Update if your backend runs on a different port."
          />
        </div>
      </div>

      {/* CLI Tools */}
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-secondary/10 flex items-center justify-center">
            <Terminal className="w-4 h-4 text-accent-secondary" />
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-text-primary">LLM CLI Tools</h2>
            <p className="text-xs text-text-muted">Claude CLI and Codex CLI for citation-grounded Q&amp;A.</p>
          </div>
          {cliStatus && (
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              cliStatus.all_available
                ? 'bg-success/10 text-success'
                : 'bg-error/10 text-error'
            }`}>
              {cliStatus.clis.filter((c) => c.found).length}/{cliStatus.clis.length} detected
            </span>
          )}
        </div>

        <div className="p-6 space-y-3">
          {cliLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-5 h-5 text-text-muted animate-spin" />
            </div>
          ) : cliStatus?.clis ? (
            cliStatus.clis.map((cli) => (
              <CliCard
                key={cli.name}
                cli={cli}
                onInstall={!cli.found}
                onRefresh={fetchCliStatus}
              />
            ))
          ) : (
            <div className="flex items-center gap-2 text-sm text-error">
              <AlertCircle className="w-4 h-4" />
              Failed to check CLI status. Is the backend running?
            </div>
          )}

          <div className="mt-3 flex items-start gap-2 p-3 rounded-lg bg-bg-secondary">
            <AlertCircle className="w-4 h-4 text-text-muted flex-shrink-0 mt-0.5" />
            <p className="text-xs text-text-muted leading-relaxed">
              CLI tools must be installed on the <strong className="text-text-primary">server machine</strong>{' '}
              running the backend, not on the client. Both tools use your existing API keys — Claude uses
              Anthropic, Codex uses OpenAI.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Reference */}
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <Zap className="w-4 h-4 text-accent-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-text-primary">Quick Reference</h2>
            <p className="text-xs text-text-muted">Current port configuration.</p>
          </div>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Frontend', port: '3000', url: frontendUrl },
              { label: 'Backend API', port: '5001', url: backendUrl },
            ].map(({ label, port, url }) => (
              <div key={label} className="bg-bg-secondary rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</span>
                  <span className="text-xs font-mono text-accent-primary">:{port}</span>
                </div>
                <p className="text-sm font-mono text-text-primary break-all">{url}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-bg-secondary">
            <AlertCircle className="w-4 h-4 text-text-muted flex-shrink-0 mt-0.5" />
            <p className="text-xs text-text-muted leading-relaxed">
              Both servers must be running simultaneously. If connecting from outside your local network,
              you&apos;ll need to configure port forwarding on your router and use your public IP address.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
