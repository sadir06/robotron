import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Markdown from 'react-markdown';
import {
  BrainCircuit,
  Play,
  Loader2,
  Wrench,
  MessageSquare,
  FileJson,
  ChevronDown,
  ChevronRight,
  Sparkles,
  AlertTriangle,
  Filter,
  Database,
} from 'lucide-react';
import './AgentPanel.css';

interface AgentStep {
  type: 'iteration' | 'thinking' | 'tool_call' | 'tool_result' | 'training_policy' | 'final_report' | 'done' | 'error';
  content?: string;
  name?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  policy?: Record<string, unknown>;
  number?: number;
  max?: number;
  usage?: { input_tokens: number; output_tokens: number };
  id?: string;
}

interface SessionOption {
  session_id: string;
  total: number;
  good: number;
  faulty: number;
}

export default function AgentPanel() {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [running, setRunning] = useState(false);
  const [prompt, setPrompt] = useState(
    'Analyze all QC pipeline data, assess data quality, and generate a LeRobot-compatible training policy for autonomous sorting.'
  );
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const traceEndRef = useRef<HTMLDivElement>(null);

  // Event range filters
  const [sessions, setSessions] = useState<SessionOption[]>([]);
  const [selectedSession, setSelectedSession] = useState<string>('all');
  const [labelFilter, setLabelFilter] = useState<string>('all');
  const [eventLimit, setEventLimit] = useState<number>(200);

  // Fetch available sessions on mount
  useEffect(() => {
    fetch('/api/events?limit=10000')
      .then((r) => r.json())
      .then((events: Array<{ session_id: string; label: string }>) => {
        const map = new Map<string, { total: number; good: number; faulty: number }>();
        for (const e of events) {
          const s = map.get(e.session_id) || { total: 0, good: 0, faulty: 0 };
          s.total++;
          if (e.label === 'GOOD') s.good++;
          if (e.label === 'FAULTY') s.faulty++;
          map.set(e.session_id, s);
        }
        setSessions(
          Array.from(map.entries()).map(([session_id, v]) => ({ session_id, ...v }))
        );
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    traceEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps]);

  // Build a prompt that includes the filter context
  const buildPrompt = () => {
    let base = prompt;
    const filters: string[] = [];
    if (selectedSession !== 'all') filters.push(`Focus on session_id="${selectedSession}".`);
    if (labelFilter !== 'all') filters.push(`Only analyze ${labelFilter} events.`);
    if (eventLimit !== 200) filters.push(`Limit analysis to ${eventLimit} most recent events.`);
    if (filters.length > 0) base += '\n\nFilters: ' + filters.join(' ');
    return base;
  };

  const runAgent = async () => {
    setRunning(true);
    setSteps([]);
    setPolicy(null);

    try {
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: buildPrompt() }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: AgentStep = JSON.parse(line.slice(6));
              setSteps((prev) => [...prev, event]);
              if (event.type === 'training_policy') setPolicy(event.policy ?? null);
              if (event.type === 'done') setRunning(false);
            } catch {
              /* skip malformed */
            }
          }
        }
      }
    } catch (err) {
      setSteps((prev) => [...prev, { type: 'error', content: String(err) }]);
    }
    setRunning(false);
  };

  // Determine which thinking blocks are "stale" (not the latest one)
  const lastThinkingIdx = (() => {
    for (let i = steps.length - 1; i >= 0; i--) {
      if (steps[i].type === 'thinking') return i;
    }
    return -1;
  })();

  return (
    <div className="agent-panel">
      {/* Header */}
      <div className="agent-header">
        <div className="agent-header-left">
          <div className="agent-icon-box">
            <Sparkles size={14} />
          </div>
          <div>
            <h2 className="agent-title">AI TRAINING POLICY AGENT</h2>
            <p className="agent-subtitle">Anthropic Claude // Agentic Tool-Use Loop</p>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="agent-filter-bar">
        <div className="agent-filter-label">
          <Filter size={10} />
          <span>EVENT RANGE</span>
        </div>

        <div className="agent-filter-group">
          <label className="agent-filter-item">
            <span>Session</span>
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              disabled={running}
              className="agent-select"
            >
              <option value="all">All Sessions ({sessions.reduce((a, s) => a + s.total, 0)})</option>
              {sessions.map((s) => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id} ({s.total} events)
                </option>
              ))}
            </select>
          </label>

          <label className="agent-filter-item">
            <span>Label</span>
            <select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              disabled={running}
              className="agent-select"
            >
              <option value="all">All Labels</option>
              <option value="GOOD">GOOD only</option>
              <option value="FAULTY">FAULTY only</option>
            </select>
          </label>

          <label className="agent-filter-item">
            <span>Limit</span>
            <select
              value={eventLimit}
              onChange={(e) => setEventLimit(Number(e.target.value))}
              disabled={running}
              className="agent-select"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={10000}>All</option>
            </select>
          </label>
        </div>

        {selectedSession !== 'all' && (
          <div className="agent-filter-summary">
            <Database size={10} />
            <span>
              {sessions.find((s) => s.session_id === selectedSession)?.good ?? 0} good
              {' / '}
              {sessions.find((s) => s.session_id === selectedSession)?.faulty ?? 0} faulty
            </span>
          </div>
        )}
      </div>

      {/* Prompt bar */}
      <div className="agent-prompt-bar">
        <input
          className="agent-prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what to analyze..."
          disabled={running}
        />
        <button className="agent-run-btn" onClick={runAgent} disabled={running}>
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? 'RUNNING...' : 'RUN AGENT'}
        </button>
      </div>

      {/* Trace */}
      <div className="agent-trace custom-scrollbar">
        {steps.length === 0 && !running && (
          <div className="agent-empty">
            <BrainCircuit size={32} />
            <p>Agent ready</p>
            <p className="agent-empty-sub">
              Click RUN AGENT to analyze QC data and generate a training policy
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {steps.map((step, idx) => (
            <StepCard
              key={idx}
              step={step}
              isStaleThinking={step.type === 'thinking' && idx !== lastThinkingIdx}
            />
          ))}
        </AnimatePresence>
        <div ref={traceEndRef} />
      </div>

      {/* Policy output */}
      {policy && (
        <div className="agent-policy-section">
          <div className="agent-policy-header">
            <FileJson size={14} />
            <span>GENERATED TRAINING POLICY</span>
          </div>
          <pre className="agent-policy-json custom-scrollbar">
            {JSON.stringify(policy, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function StepCard({ step, isStaleThinking }: { step: AgentStep; isStaleThinking: boolean }) {
  const [expanded, setExpanded] = useState(false);

  if (step.type === 'iteration') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="step-iteration"
      >
        <span className="step-iter-badge">STEP {step.number}/{step.max}</span>
      </motion.div>
    );
  }

  if (step.type === 'thinking') {
    // Stale thinking blocks collapse to a single-line summary
    if (isStaleThinking) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="step-card step-thinking step-thinking-stale"
        >
          <div
            className="step-card-header"
            onClick={() => setExpanded(!expanded)}
            style={{ cursor: 'pointer', marginBottom: expanded ? '0.3rem' : 0 }}
          >
            <MessageSquare size={12} />
            <span className="step-type-label">REASONING</span>
            <span className="step-thinking-preview">
              {(step.content || '').slice(0, 80)}...
            </span>
            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </div>
          {expanded && <div className="step-thinking-text markdown-body"><Markdown>{step.content || ''}</Markdown></div>}
        </motion.div>
      );
    }

    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="step-card step-thinking"
      >
        <div className="step-card-header">
          <MessageSquare size={12} />
          <span className="step-type-label">REASONING</span>
        </div>
        <div className="step-thinking-text markdown-body"><Markdown>{step.content || ''}</Markdown></div>
      </motion.div>
    );
  }

  if (step.type === 'tool_call') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="step-card step-tool-call"
      >
        <div className="step-card-header" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
          <Wrench size={12} />
          <span className="step-type-label">TOOL CALL</span>
          <span className="step-tool-name">{step.name}</span>
          {step.input && Object.keys(step.input).length > 0 && (
            expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />
          )}
        </div>
        {expanded && step.input && Object.keys(step.input).length > 0 && (
          <pre className="step-json">{JSON.stringify(step.input, null, 2)}</pre>
        )}
      </motion.div>
    );
  }

  if (step.type === 'tool_result') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="step-card step-tool-result"
      >
        <div className="step-card-header" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
          <FileJson size={12} />
          <span className="step-type-label">RESULT</span>
          <span className="step-tool-name">{step.name}</span>
          {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </div>
        {expanded && step.output && (
          <pre className="step-json">{JSON.stringify(step.output, null, 2)}</pre>
        )}
      </motion.div>
    );
  }

  if (step.type === 'final_report') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="step-card step-report"
      >
        <div className="step-card-header">
          <Sparkles size={12} />
          <span className="step-type-label">FINAL REPORT</span>
        </div>
        <div className="step-report-text markdown-body"><Markdown>{step.content || ''}</Markdown></div>
      </motion.div>
    );
  }

  if (step.type === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="step-card step-error"
      >
        <div className="step-card-header">
          <AlertTriangle size={12} />
          <span className="step-type-label">ERROR</span>
        </div>
        <div className="step-error-text">{step.content}</div>
      </motion.div>
    );
  }

  if (step.type === 'done') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="step-done"
      >
        <span className="step-done-badge">AGENT COMPLETE</span>
        {step.usage && (
          <span className="step-done-usage">
            {step.usage.input_tokens.toLocaleString()} in / {step.usage.output_tokens.toLocaleString()} out tokens
          </span>
        )}
      </motion.div>
    );
  }

  return null;
}
