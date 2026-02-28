import React, { useState, useEffect, useRef } from 'react';
import './index.css';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  Cpu, 
  Terminal, 
  Settings, 
  Camera,
  Layers,
  Clock,
  Zap,
  RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface PipelineEvent {
  event: string;
  label?: string;
  action?: string;
  latency_ms?: number;
  frame?: string;
  item_id?: number;
  raw_response?: string;
  message?: string;
}

export default function App() {
  const [logs, setLogs] = useState<PipelineEvent[]>([]);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [status, setStatus] = useState<'disconnected' | 'connected' | 'error'>('disconnected');
  const [stats, setStats] = useState({ processed: 0, faults: 0, goods: 0 });
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`
    
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setStatus('connected')
      setLogs(prev => [...prev, { event: 'connected', message: 'Connected to pipeline' }])
    }

    ws.onmessage = (event) => {
      const data: PipelineEvent = JSON.parse(event.data)
      
      // Update frame
      if (data.frame) {
        setCurrentFrame(`data:image/jpeg;base64,${data.frame}`)
      }

      // Only log classification events (not every frame)
      if (data.event === 'item_processed') {
        setStats(prev => ({
          ...prev,
          processed: prev.processed + 1,
          faults: prev.faults + (data.label === 'FAULTY' ? 1 : 0),
        }))
        setLogs(prev => {
          const updated = [...prev, data]
          return updated.slice(-100) // Keep last 100 logs
        })
      } else if (data.event === 'item_nothing') {
        setStats(prev => ({
          ...prev,
          goods: prev.goods + 1,
        }))
        setLogs(prev => {
          const updated = [...prev, data]
          return updated.slice(-100) // Keep last 100 logs
        })
      } else if (data.event === 'frame') {
        // Update live frame from continuous stream
        if (data.frame) {
          setCurrentFrame(`data:image/jpeg;base64,${data.frame}`)
        }
      } else {
        // Log other events (started, error, etc.)
        setLogs(prev => {
          const updated = [...prev, data]
          return updated.slice(-100)
        })
      }
    }

    ws.onerror = () => {
      setStatus('error')
      setLogs(prev => [...prev, { event: 'error', message: 'WebSocket connection error' }])
    }

    ws.onclose = () => {
      setStatus('disconnected')
      setLogs(prev => [...prev, { event: 'disconnected', message: 'Disconnected from pipeline' }])
      // Attempt reconnect after 3 seconds
      setTimeout(() => {
        window.location.reload()
      }, 3000)
    }

    wsRef.current = ws

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    }
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getStatusClass = () => {
    switch (status) {
      case 'connected': return 'status-connected';
      case 'error': return 'status-error';
      default: return 'status-disconnected';
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="logo-box">
            <Cpu size={20} color="black" />
          </div>
          <div className="logo-text">
            <h1>ROBOTRON <span style={{ color: 'var(--emerald-500)' }}>v2.4</span></h1>
            <p>Pipeline Monitor System</p>
          </div>
        </div>

        <div className="header-right">
          <div className={`status-badge ${getStatusClass()}`}>
            <span className="status-dot" style={{ backgroundColor: 'currentColor' }} />
            {status.toUpperCase()}
          </div>
          <button className="p-2" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-zinc-500)' }}>
            <Settings size={16} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Left Column: Feed & Stats */}
        <div className="left-column">
          {/* Camera Feed Container */}
          <div className="feed-container">
            <div className="feed-label-left">
              <Camera size={12} color="var(--emerald-500)" />
              <span className="label-text">CAM_01 // LIVE</span>
            </div>
            
            <div className="feed-label-right">
              <div style={{ width: '6px', height: '6px', backgroundColor: 'var(--rose-600)' }} />
              <span className="label-text">RECORDING</span>
            </div>

            <div className="feed-view">
              {currentFrame ? (
                <img 
                  src={currentFrame} 
                  alt="Camera Feed" 
                  className="feed-img"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="feed-placeholder">
                  <RefreshCw size={40} className="animate-spin" style={{ opacity: 0.4 }} />
                  <p style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.3em' }}>Signal Search...</p>
                </div>
              )}
            </div>

            {/* Overlay Grid Lines */}
            <div className="feed-grid-overlay" />
          </div>

          {/* Stats Grid */}
          <div className="stats-grid">
            <StatCard 
              label="Processed" 
              value={stats.processed} 
              icon={<Layers size={12} />}
              color="emerald"
            />
            <StatCard 
              label="Faults" 
              value={stats.faults} 
              icon={<AlertTriangle size={12} />}
              color="rose"
              isAlert={stats.faults > 0}
            />
            <StatCard 
              label="Passed" 
              value={stats.goods} 
              icon={<CheckCircle2 size={12} />}
              color="sky"
            />
          </div>
        </div>

        {/* Right Column: Logs */}
        <aside className="aside-logs">
          <div className="aside-header">
            <div className="aside-title">
              <Terminal size={12} color="var(--emerald-500)" />
              <h2>System Logs</h2>
            </div>
            <span className="aside-version">v2.4.0-stable</span>
          </div>

          <div className="logs-container custom-scrollbar">
            <div className="logs-list">
              <AnimatePresence initial={false}>
                {logs.length === 0 ? (
                  <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-zinc-800)', textTransform: 'uppercase', letterSpacing: '0.2em', fontSize: '9px' }}>
                    Awaiting events...
                  </div>
                ) : (
                  logs.map((log, idx) => (
                    <LogEntry key={`${idx}-${log.event}`} log={log} />
                  ))
                )}
              </AnimatePresence>
              <div ref={logsEndRef} />
            </div>
          </div>
        </aside>
      </main>

      {/* Footer Status Bar */}
      <footer className="footer">
        <div className="footer-left">
          <div className="footer-item">
            <Clock size={12} />
            <span>UPTIME: 04:12:44</span>
          </div>
          <div className="footer-item">
            <Zap size={12} />
            <span>LATENCY: 12ms</span>
          </div>
        </div>
        <div className="footer-right">
          SECURE_NODE: 0x82...F41
        </div>
      </footer>
    </div>
  );
}

const StatCard: React.FC<{ 
  label: string; 
  value: number; 
  icon: React.ReactNode; 
  color: 'emerald' | 'rose' | 'sky'; 
  isAlert?: boolean;
}> = ({ label, value, icon, color, isAlert }) => {
  const colorVar = `var(--${color}-500)`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`stat-card ${isAlert ? 'stat-card-alert' : ''}`}
    >
      <div className="stat-card-header">
        <span className="stat-label">{label}</span>
        <div className="stat-icon-box" style={{ borderColor: `rgba(${color === 'emerald' ? '16, 185, 129' : color === 'rose' ? '244, 63, 94' : '14, 165, 233'}, 0.2)`, color: colorVar, backgroundColor: `rgba(${color === 'emerald' ? '16, 185, 129' : color === 'rose' ? '244, 63, 94' : '14, 165, 233'}, 0.1)` }}>
          {icon}
        </div>
      </div>
      <div className="stat-value-container">
        <motion.span 
          key={value}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
          className="stat-value"
        >
          {value.toLocaleString()}
        </motion.span>
        <span className="stat-unit">Units</span>
      </div>
    </motion.div>
  );
};

const LogEntry: React.FC<{ log: PipelineEvent }> = ({ log }) => {
  const getEventStyle = () => {
    switch (log.event) {
      case 'item_processed': 
        return {
          borderColor: log.label === 'FAULTY' ? 'var(--rose-900)' : 'var(--emerald-900)',
          backgroundColor: log.label === 'FAULTY' ? 'rgba(76, 5, 25, 0.1)' : 'rgba(6, 78, 59, 0.1)'
        };
      case 'error': 
        return {
          borderColor: 'var(--rose-500)',
          backgroundColor: 'rgba(244, 63, 94, 0.1)'
        };
      case 'connected': 
        return {
          borderColor: 'var(--emerald-500)',
          backgroundColor: 'rgba(16, 185, 129, 0.1)'
        };
      default: 
        return {
          borderColor: 'var(--border-zinc-800)',
          backgroundColor: 'rgba(39, 39, 42, 0.1)'
        };
    }
  };

  const style = getEventStyle();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="log-entry"
      style={style}
    >
      <div className="log-entry-header">
        <span className="log-time">{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        <span className="log-event-name" style={{ color: log.event === 'error' ? 'var(--rose-600)' : 'var(--text-zinc-500)' }}>
          {log.event.replace('_', ' ')}
        </span>
      </div>
      
      <div className="log-details">
        {log.label && (
          <span className="log-label-badge" style={{ backgroundColor: log.label === 'FAULTY' ? 'var(--rose-900)' : 'var(--emerald-900)', color: log.label === 'FAULTY' ? '#fecaca' : '#d1fae5' }}>
            {log.label}
          </span>
        )}
        
        {log.action && (
          <span className="log-action-text">
            ACTION: <span style={{ color: 'var(--amber-600)', fontWeight: 700 }}>{log.action.toUpperCase()}</span>
          </span>
        )}

        {log.latency_ms && (
          <span className="log-latency-text">
            LATENCY: <span style={{ color: 'var(--emerald-900)' }}>{log.latency_ms}ms</span>
          </span>
        )}

        {log.message && (
          <span className="log-message-text">{log.message}</span>
        )}
      </div>

      {log.raw_response && (
        <div className="log-vlm-box">
          <span style={{ color: 'var(--emerald-900)', marginRight: '4px', fontWeight: 700 }}>VLM_OUT:</span>
          "{log.raw_response}"
        </div>
      )}
    </motion.div>
  );
};

