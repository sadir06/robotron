"""Tool definitions and handlers for the QC optimizer agent."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from data.event_store import get_events, get_session_stats, _conn

_ROOT = Path(__file__).resolve().parent.parent

# ── Tool schemas (Anthropic tool_use format) ─────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_qc_stats",
        "description": (
            "Get aggregated QC pipeline statistics. Returns total items processed, "
            "good/faulty/nothing counts, fault rate, average VLM latency, and session info. "
            "Also returns cross-session totals. Call this first to understand overall performance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Filter to a specific session ID. Omit for current session.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_events",
        "description": (
            "Query individual QC classification events from the database. "
            "Returns raw event data including VLM responses, latencies, labels, and robot actions. "
            "Use this to investigate specific patterns, edge cases, or anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "enum": ["GOOD", "FAULTY", "NOTHING"],
                    "description": "Filter by classification label.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Filter by session ID.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max events to return (default 50, max 500).",
                },
                "min_latency_ms": {
                    "type": "number",
                    "description": "Only return events slower than this threshold.",
                },
                "max_latency_ms": {
                    "type": "number",
                    "description": "Only return events faster than this threshold.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "analyze_vlm_responses",
        "description": (
            "Perform pattern analysis on VLM response texts. "
            "Detects format violations (responses not ending with GOOD/FAULTY/NOTHING), "
            "identifies potential hallucinations (description contradicts label), "
            "computes response diversity metrics, and produces latency distribution stats. "
            "This is the primary tool for understanding VLM behaviour."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Filter to a specific session. Omit for all sessions.",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "format_compliance",
                        "response_diversity",
                        "label_consistency",
                        "latency_distribution",
                        "all",
                    ],
                    "description": "Type of analysis to run. Defaults to 'all'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "read_current_prompt",
        "description": (
            "Read the current VLM system prompt used for candy inspection classification. "
            "Returns the full text of prompts/fault_detection.txt."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "analyze_trajectories",
        "description": (
            "Analyze the robot arm trajectory files used for sorting. "
            "Returns metadata per trajectory: duration, frame count, sampling rate, "
            "per-motor ranges of motion, gripper range, start/end positions. "
            "Useful for understanding the action space and suggesting policy parameters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trajectory_name": {
                    "type": "string",
                    "description": (
                        "Specific trajectory to analyze (e.g. 'left_pick', 'right'). "
                        "Omit to analyze all trajectories."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_training_policy",
        "description": (
            "Generate and save a LeRobot-compatible training policy JSON based on analysis. "
            "The policy includes observation/action spaces, reward signals, data splits, "
            "hyperparameters, and data quality notes. "
            "Call this AFTER you have analyzed the data with the other tools. "
            "The policy is saved to config/policies/<timestamp>.json."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy": {
                    "type": "object",
                    "description": (
                        "The full training policy object. Must include: policy_name, "
                        "data_summary, observation_space, action_space, reward_signals, "
                        "training_config, data_quality_notes, recommendations."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of the design choices in this policy.",
                },
            },
            "required": ["policy", "reasoning"],
        },
    },
]


# ── Handlers ──────────────────────────────────────────────────────────

def _handle_get_qc_stats(session_id: str | None = None) -> dict:
    stats = get_session_stats(session_id=session_id)
    conn = _conn()
    row = conn.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN label='GOOD' THEN 1 ELSE 0 END) AS good, "
        "SUM(CASE WHEN label='FAULTY' THEN 1 ELSE 0 END) AS faulty, "
        "SUM(CASE WHEN label='NOTHING' THEN 1 ELSE 0 END) AS nothing_count, "
        "AVG(vlm_latency_ms) AS avg_latency, "
        "COUNT(DISTINCT session_id) AS sessions "
        "FROM qc_events"
    ).fetchone()
    return {
        "current_session": stats.model_dump(),
        "all_time": dict(row),
    }


def _handle_query_events(
    label: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
    min_latency_ms: float | None = None,
    max_latency_ms: float | None = None,
) -> list[dict]:
    conn = _conn()
    query = (
        "SELECT id, session_id, timestamp, item_id, label, "
        "raw_vlm_response, vlm_latency_ms, vlm_model, action, "
        "trajectory_file, stability_frames, outcome "
        "FROM qc_events WHERE 1=1"
    )
    params: list = []
    if label:
        query += " AND label = ?"
        params.append(label)
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if min_latency_ms is not None:
        query += " AND vlm_latency_ms >= ?"
        params.append(min_latency_ms)
    if max_latency_ms is not None:
        query += " AND vlm_latency_ms <= ?"
        params.append(max_latency_ms)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(min(limit, 500))
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def _handle_analyze_vlm_responses(
    session_id: str | None = None,
    analysis_type: str = "all",
) -> dict:
    events = get_events(session_id=session_id, limit=10000)
    results: dict[str, Any] = {}

    if analysis_type in ("format_compliance", "all"):
        compliant = 0
        violations: list[dict] = []
        for e in events:
            raw = e["raw_vlm_response"] or ""
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            last = lines[-1].upper() if lines else ""
            if last in ("GOOD", "FAULTY", "NOTHING"):
                compliant += 1
            else:
                violations.append({"id": e["id"], "response": raw, "label": e["label"]})
        results["format_compliance"] = {
            "total": len(events),
            "compliant": compliant,
            "compliance_rate": round(compliant / len(events), 4) if events else 0,
            "violations": violations[:20],
        }

    if analysis_type in ("response_diversity", "all"):
        by_label: dict[str, list[str]] = {}
        for e in events:
            by_label.setdefault(e["label"], []).append(e["raw_vlm_response"] or "")
        diversity: dict[str, Any] = {}
        for lbl, responses in by_label.items():
            counter = Counter(responses)
            diversity[lbl] = {
                "total": len(responses),
                "unique_responses": len(counter),
                "top_responses": counter.most_common(5),
            }
        results["response_diversity"] = diversity

    if analysis_type in ("label_consistency", "all"):
        suspicious: list[dict] = []
        for e in events:
            raw = (e["raw_vlm_response"] or "").lower()
            lbl = e["label"]
            if lbl == "GOOD" and any(w in raw for w in ["torn", "open", "exposed", "damaged", "unsealed"]):
                suspicious.append({"id": e["id"], "label": lbl, "response": e["raw_vlm_response"]})
            elif lbl == "FAULTY" and any(w in raw for w in ["perfectly sealed", "intact", "no defects", "undamaged"]):
                suspicious.append({"id": e["id"], "label": lbl, "response": e["raw_vlm_response"]})
        results["label_consistency"] = {
            "total_checked": len(events),
            "suspicious_count": len(suspicious),
            "suspicious_events": suspicious[:20],
        }

    if analysis_type in ("latency_distribution", "all"):
        latencies = sorted(e["vlm_latency_ms"] for e in events if e["vlm_latency_ms"])
        if latencies:
            n = len(latencies)
            results["latency_distribution"] = {
                "count": n,
                "min_ms": round(min(latencies), 1),
                "max_ms": round(max(latencies), 1),
                "mean_ms": round(sum(latencies) / n, 1),
                "median_ms": round(latencies[n // 2], 1),
                "p95_ms": round(latencies[int(n * 0.95)], 1),
                "p99_ms": round(latencies[int(n * 0.99)], 1),
                "slow_calls_over_500ms": sum(1 for l in latencies if l > 500),
            }

    return results


def _handle_read_current_prompt() -> dict:
    prompt_path = _ROOT / "prompts" / "fault_detection.txt"
    text = prompt_path.read_text() if prompt_path.exists() else "(no prompt file found)"
    return {"path": str(prompt_path), "content": text, "line_count": len(text.splitlines())}


def _handle_analyze_trajectories(trajectory_name: str | None = None) -> dict:
    traj_dir = _ROOT / "trajectories"
    if not traj_dir.exists():
        return {"error": "trajectories/ directory not found"}

    files = (
        [traj_dir / f"{trajectory_name}.json"]
        if trajectory_name
        else list(traj_dir.glob("*.json"))
    )
    results: dict[str, Any] = {}
    for f in files:
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        frames = data.get("frames", [])
        motors = data.get("motors", [])
        hz = data.get("hz", 30)
        duration = frames[-1]["t"] if frames else 0

        motor_analysis: dict[str, Any] = {}
        for motor in motors:
            key = f"{motor}.pos"
            positions = [fr[key] for fr in frames if key in fr]
            if positions:
                motor_analysis[motor] = {
                    "min": round(min(positions), 2),
                    "max": round(max(positions), 2),
                    "range": round(max(positions) - min(positions), 2),
                    "start": round(positions[0], 2),
                    "end": round(positions[-1], 2),
                }

        gripper_positions = [fr.get("gripper.pos", 0) for fr in frames]
        results[f.stem] = {
            "direction": data.get("direction"),
            "frame_count": len(frames),
            "duration_sec": round(duration, 2),
            "hz": hz,
            "motors": motors,
            "motor_ranges": motor_analysis,
            "gripper_range": {
                "min": round(min(gripper_positions), 2) if gripper_positions else 0,
                "max": round(max(gripper_positions), 2) if gripper_positions else 0,
            },
        }
    return results


def _handle_generate_training_policy(policy: dict, reasoning: str) -> dict:
    policies_dir = _ROOT / "config" / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    policy_file = policies_dir / f"policy_{ts}.json"

    payload = {
        **policy,
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": "claude-sonnet-4-20250514",
        "reasoning": reasoning,
    }
    policy_file.write_text(json.dumps(payload, indent=2))
    return {"status": "policy_saved", "path": str(policy_file), "policy": payload}


# ── Dispatcher ────────────────────────────────────────────────────────

_HANDLERS = {
    "get_qc_stats": _handle_get_qc_stats,
    "query_events": _handle_query_events,
    "analyze_vlm_responses": _handle_analyze_vlm_responses,
    "read_current_prompt": _handle_read_current_prompt,
    "analyze_trajectories": _handle_analyze_trajectories,
    "generate_training_policy": _handle_generate_training_policy,
}


def dispatch_tool(name: str, input_data: dict) -> Any:
    """Route a tool call to its handler."""
    handler = _HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(**input_data)
