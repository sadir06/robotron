"""
Agentic QC Pipeline Optimizer — Anthropic tool_use loop.

Analyzes accumulated QC data and generates a LeRobot-compatible training policy.
Streams every reasoning step + tool call so the frontend can render a live trace.
"""

import json
from datetime import datetime
from typing import AsyncIterator

import anthropic

from agent.tools import TOOLS, dispatch_tool

AGENT_SYSTEM_PROMPT = """\
You are a **Robotics Training Policy Architect** for a candy-factory QC sorting robot.

## System overview
A conveyor belt carries candy past a camera. A VLM (Vision Language Model) classifies
each item as GOOD (sealed wrapper), FAULTY (damaged/open wrapper), or NOTHING (empty tray).
Based on the classification, a 6-DOF robot arm replays a pre-recorded trajectory to sort
the item into the correct pile (left_pick for GOOD, right_pick for FAULTY).

Every classification + motor action is logged with Pydantic-validated schemas into a
SQLite database. This accumulated data is the training dataset for transitioning from
manual teleoperation to autonomous policy learning using LeRobot.

## Your mission
1. **Analyze** the accumulated QC event data — classifications, VLM responses, latency
   distributions, error patterns, trajectory profiles.
2. **Assess** data quality — class imbalance, hallucinations, format compliance,
   response diversity.
3. **Generate** a concrete LeRobot-compatible training policy JSON that defines:
   - Observation space (image shape, VLM features)
   - Action space (trajectory selection, motor names, joint limits)
   - Reward signals (accuracy, speed, sort success) with weights
   - Training hyperparameters (algorithm, batch size, learning rate, epochs, splits)
   - Data quality notes and recommendations for collecting better data

## Rules
- Always call tools to gather real data before making claims. Never guess.
- Cite specific numbers from the data (e.g. "74% fault rate across 143 events").
- Think step-by-step. Explain your reasoning clearly.
- End with a comprehensive final report summarizing findings, the generated policy,
  and actionable next steps.
"""


async def run_agent(
    user_request: str = (
        "Analyze all QC pipeline data, assess data quality, and generate "
        "a LeRobot-compatible training policy for autonomous sorting."
    ),
    max_iterations: int = 15,
) -> AsyncIterator[dict]:
    """Run the agentic loop. Yields events for SSE streaming to the frontend."""
    client = anthropic.Anthropic()

    messages: list[dict] = [{"role": "user", "content": user_request}]

    for iteration in range(1, max_iterations + 1):
        yield {"type": "iteration", "number": iteration, "max": max_iterations}

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=AGENT_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Emit all content blocks
        for block in response.content:
            if block.type == "text":
                yield {"type": "thinking", "content": block.text}
            elif block.type == "tool_use":
                yield {
                    "type": "tool_call",
                    "name": block.name,
                    "input": block.input,
                    "id": block.id,
                }

        # Done — extract final text
        if response.stop_reason == "end_turn":
            final_text = "\n".join(
                block.text for block in response.content if block.type == "text"
            )
            yield {"type": "final_report", "content": final_text}
            yield {
                "type": "done",
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
            return

        # Tool use — execute and continue
        if response.stop_reason == "tool_use":
            messages.append(
                {"role": "assistant", "content": response.content}
            )

            tool_results: list[dict] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = dispatch_tool(block.name, block.input)
                    yield {"type": "tool_result", "name": block.name, "output": result}

                    # Special event when a training policy is generated
                    if block.name == "generate_training_policy" and isinstance(result, dict):
                        yield {"type": "training_policy", "policy": result.get("policy", result)}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
                except Exception as e:
                    error_msg = f"Tool error ({block.name}): {e}"
                    yield {"type": "error", "content": error_msg}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": str(e)}),
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})

    yield {"type": "error", "content": "Max iterations reached"}
    yield {"type": "done"}
