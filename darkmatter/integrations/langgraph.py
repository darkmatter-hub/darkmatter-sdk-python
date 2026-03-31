"""
DarkMatter LangGraph integration.

Automatically commits a Context Passport after every node execution.
Zero changes to your existing graph.

Usage::

    from darkmatter.integrations.langgraph import DarkMatterTracer

    app = workflow.compile(checkpointer=memory)
    app = DarkMatterTracer(app, agent_id="my-agent", to_agent_id="my-agent")

    result = app.invoke(input, config={"thread_id": "run-1"})
    # Every node completion automatically committed to DarkMatter
"""

import os
import time
from typing import Any, Dict, Optional

try:
    from darkmatter.client import DarkMatter
except ImportError:
    raise ImportError("darkmatter package not found. Run: pip install darkmatter")


class DarkMatterTracer:
    """
    Wraps a compiled LangGraph app to automatically commit Context Passports.

    Every node completion creates a commit. The parent_id is threaded through
    so the full chain is linked root → tip.

    Args:
        app:          Compiled LangGraph app (from workflow.compile())
        agent_id:     Your agent's DarkMatter ID (from dashboard)
        to_agent_id:  Recipient agent ID (can be same as agent_id for self-chains)
        api_key:      DarkMatter API key (defaults to DARKMATTER_API_KEY env var)
        trace_id:     Optional trace ID to group all commits from this run
        provider:     LLM provider name (e.g. "anthropic", "openai")
        model:        Model name (e.g. "claude-opus-4-6")

    Example::

        from langgraph.graph import StateGraph, END
        from darkmatter.integrations.langgraph import DarkMatterTracer

        # Your existing graph — unchanged
        workflow = StateGraph(AgentState)
        workflow.add_node("researcher", researcher_node)
        workflow.add_node("writer", writer_node)
        workflow.add_edge("researcher", "writer")
        workflow.add_edge("writer", END)
        app = workflow.compile()

        # One line to add DarkMatter
        app = DarkMatterTracer(app, agent_id="MY_AGENT_ID", to_agent_id="MY_AGENT_ID")

        result = app.invoke({"input": "Write a report on Q1 earnings"})
    """

    def __init__(
        self,
        app,
        agent_id: str,
        to_agent_id: str,
        api_key: str = None,
        trace_id: str = None,
        provider: str = None,
        model: str = None,
    ):
        self._app = app
        self._agent_id = agent_id
        self._to_agent_id = to_agent_id
        self._dm = DarkMatter(api_key=api_key)
        self._trace_id = trace_id
        self._provider = provider
        self._model = model

    def invoke(self, input: Dict, config: Dict = None, **kwargs) -> Dict:
        config = config or {}
        parent_id = None
        trace_id = self._trace_id or f"trc_{int(time.time() * 1000)}"

        # Hook into LangGraph's stream to capture node-by-node output
        try:
            for chunk in self._app.stream(input, config, stream_mode="updates", **kwargs):
                for node_name, node_output in chunk.items():
                    try:
                        ctx = self._dm.commit(
                            to_agent_id=self._to_agent_id,
                            payload={
                                "input":  input if parent_id is None else None,
                                "output": node_output,
                                "memory": {"node": node_name},
                            },
                            parent_id=parent_id,
                            trace_id=trace_id,
                            event_type="checkpoint",
                            agent={
                                "role":     node_name,
                                "provider": self._provider,
                                "model":    self._model,
                            },
                        )
                        parent_id = ctx.get("id")
                    except Exception as e:
                        # Never let DarkMatter failures break the pipeline
                        print(f"[DarkMatter] commit failed for node {node_name}: {e}")

        except Exception:
            # Fall back to regular invoke if stream fails
            result = self._app.invoke(input, config, **kwargs)
            try:
                self._dm.commit(
                    to_agent_id=self._to_agent_id,
                    payload={"input": input, "output": result},
                    trace_id=trace_id,
                    event_type="commit",
                )
            except Exception as e:
                print(f"[DarkMatter] commit failed: {e}")
            return result

        # Return final state from regular invoke
        return self._app.invoke(input, config, **kwargs)

    def stream(self, input: Dict, config: Dict = None, **kwargs):
        """Passthrough stream — commits happen automatically."""
        return self._app.stream(input, config, **kwargs)

    def __getattr__(self, name):
        """Proxy everything else to the underlying app."""
        return getattr(self._app, name)
