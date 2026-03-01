import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  Database,
  Download,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
} from 'lucide-react';

interface QCEvent {
  id: number;
  session_id: string;
  timestamp: string;
  item_id: number;
  label: string;
  raw_vlm_response: string;
  vlm_latency_ms: number;
  vlm_model: string;
  action: string | null;
  trajectory_file: string | null;
  stability_frames: number;
  outcome: string;
}

interface SessionStats {
  session_id: string;
  started_at: string;
  total_items: number;
  good_count: number;
  faulty_count: number;
  nothing_count: number;
  avg_vlm_latency_ms: number;
  fault_rate: number;
}

export default function TrainingData() {
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [events, setEvents] = useState<QCEvent[]>([]);
  const [exporting, setExporting] = useState(false);

  const fetchData = () => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => {});

    fetch('/api/events?limit=200')
      .then(r => r.json())
      .then(setEvents)
      .catch(() => {});
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const classifiedEvents = events.filter(e => e.label !== 'NOTHING');

  const handleExport = () => {
    setExporting(true);
    window.open('/api/export/training', '_blank');
    setTimeout(() => setExporting(false), 1500);
  };

  return (
    <div className="td-panel">
      {/* Header with metrics + export */}
      <div className="td-header">
        <div className="td-header-left">
          <div className="td-icon-box">
            <Database size={14} />
          </div>
          <div>
            <h2 className="td-title">TRAINING DATA</h2>
            <p className="td-subtitle">LeRobot Policy Learning // Classified Events</p>
          </div>
        </div>
        <div className="td-header-right">
          {stats && stats.total_items > 0 && (
            <span className="td-count-badge">{classifiedEvents.length} events</span>
          )}
          <button
            className="td-export-btn-sm"
            onClick={handleExport}
            disabled={classifiedEvents.length === 0 || exporting}
          >
            <Download size={12} />
            {exporting ? 'EXPORTING...' : 'EXPORT JSON'}
          </button>
        </div>
      </div>

      {/* Stats strip */}
      {stats && (
        <div className="td-stats-strip">
          <div className="td-stat-chip">
            <Gauge size={10} />
            <span className="td-stat-chip-label">FAULT RATE</span>
            <span
              className="td-stat-chip-value"
              style={{ color: stats.fault_rate > 0.15 ? 'var(--rose-500)' : 'var(--emerald-500)' }}
            >
              {(stats.fault_rate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="td-stat-chip">
            <TrendingUp size={10} />
            <span className="td-stat-chip-label">AVG LATENCY</span>
            <span className="td-stat-chip-value" style={{ color: 'var(--sky-500)' }}>
              {stats.avg_vlm_latency_ms.toFixed(0)}ms
            </span>
          </div>
          <div className="td-stat-chip">
            <CheckCircle2 size={10} />
            <span className="td-stat-chip-label">GOOD</span>
            <span className="td-stat-chip-value" style={{ color: 'var(--emerald-500)' }}>
              {stats.good_count}
            </span>
          </div>
          <div className="td-stat-chip">
            <AlertTriangle size={10} />
            <span className="td-stat-chip-label">FAULTY</span>
            <span className="td-stat-chip-value" style={{ color: 'var(--rose-500)' }}>
              {stats.faulty_count}
            </span>
          </div>
          <div className="td-stat-chip td-stat-chip-session">
            <span className="td-stat-chip-label">SESSION</span>
            <span className="td-stat-chip-value" style={{ color: 'var(--text-zinc-400)' }}>
              {stats.session_id}
            </span>
          </div>
        </div>
      )}

      {/* Events table */}
      <div className="td-body" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {classifiedEvents.length === 0 ? (
          <div className="td-empty">
            <Database size={24} />
            <p>No classification events yet</p>
            <p className="td-empty-sub">Events will appear as the pipeline processes items</p>
          </div>
        ) : (
          <div className="td-events-scroll custom-scrollbar" style={{ flex: 1 }}>
            <table className="td-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>TIME</th>
                  <th>LABEL</th>
                  <th>ACTION</th>
                  <th>LATENCY</th>
                  <th>VLM RESPONSE</th>
                </tr>
              </thead>
              <tbody>
                {classifiedEvents.map((e) => (
                  <motion.tr
                    key={e.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`td-row td-row-${e.label.toLowerCase()}`}
                  >
                    <td className="td-cell-id">{e.item_id}</td>
                    <td className="td-cell-time">
                      {new Date(e.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td>
                      <span className={`td-label-badge td-label-${e.label.toLowerCase()}`}>
                        {e.label}
                      </span>
                    </td>
                    <td className="td-cell-action">{e.action || '-'}</td>
                    <td className="td-cell-latency">{e.vlm_latency_ms}ms</td>
                    <td className="td-cell-vlm">{e.raw_vlm_response}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
