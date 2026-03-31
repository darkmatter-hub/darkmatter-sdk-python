"""
DarkMatter Python SDK — client module
"""

import os
import json
import hashlib
import time
import secrets
from typing import Optional, Any, Dict, List
from urllib import request as _request, error as _urlerr

from .exceptions import DarkMatterError, AuthError, NotFoundError

_BASE = "https://darkmatterhub.ai"


def _get_key():
    key = os.environ.get("DARKMATTER_API_KEY", "")
    if not key:
        raise AuthError(
            "No API key found. Set DARKMATTER_API_KEY environment variable "
            "or pass api_key= to DarkMatter().\n"
            "Get a free key at https://darkmatterhub.ai/signup"
        )
    return key


def _req(method: str, path: str, body=None, key: str = None, base: str = None):
    url = (base or _BASE) + path
    data = json.dumps(body).encode() if body else None
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key or _get_key()}",
    }
    req = _request.Request(url, data=data, headers=headers, method=method)
    try:
        with _request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except _urlerr.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        msg = body.get("error", str(e))
        if e.code == 401:
            raise AuthError(msg)
        if e.code == 404:
            raise NotFoundError(msg)
        raise DarkMatterError(f"HTTP {e.code}: {msg}")
    except _urlerr.URLError as e:
        raise DarkMatterError(f"Connection error: {e.reason}")


# ── Module-level convenience functions (use env key) ─────────────────────────

def commit(
    to_agent_id: str,
    payload: Dict[str, Any],
    parent_id: str = None,
    trace_id: str = None,
    branch_key: str = None,
    event_type: str = "commit",
    agent: Dict[str, str] = None,
) -> Dict:
    """
    Commit agent context to DarkMatter.

    Returns the full Context Passport object.

    Example::

        ctx = dm.commit(
            to_agent_id="agent-writer-01",
            payload={"input": prompt, "output": result},
            agent={"role": "researcher", "provider": "anthropic", "model": "claude-opus-4-6"},
        )
        print(ctx["id"])  # ctx_1234567890_abc123
    """
    body = {"toAgentId": to_agent_id, "payload": payload, "eventType": event_type}
    if parent_id:  body["parentId"] = parent_id
    if trace_id:   body["traceId"] = trace_id
    if branch_key: body["branchKey"] = branch_key
    if agent:      body["agent"] = agent
    return _req("POST", "/api/commit", body)


def pull() -> Dict:
    """
    Pull all verified contexts addressed to this agent.

    Returns::

        {
            "agentId": "...",
            "contexts": [...],
            "count": 3
        }
    """
    return _req("GET", "/api/pull")


def replay(ctx_id: str, mode: str = "full") -> Dict:
    """
    Replay the full decision path for a context chain.

    Args:
        ctx_id: The context ID (tip of chain)
        mode: "full" (includes payloads) or "summary" (metadata only)

    Returns the full replay with step-by-step chain, integrity status, and summary.
    """
    return _req("GET", f"/api/replay/{ctx_id}?mode={mode}")


def fork(ctx_id: str, to_agent_id: str = None, branch_key: str = None, payload: Dict = None) -> Dict:
    """
    Fork from a checkpoint. Creates a new branch without modifying the original chain.

    Example::

        fork_ctx = dm.fork(ctx_id, branch_key="experiment-v2")
        # continue on the fork
        dm.commit("agent-b", payload={...}, parent_id=fork_ctx["id"])
    """
    body = {}
    if to_agent_id: body["toAgentId"] = to_agent_id
    if branch_key:  body["branchKey"] = branch_key
    if payload:     body["payload"] = payload
    return _req("POST", f"/api/fork/{ctx_id}", body)


def verify(ctx_id: str) -> Dict:
    """
    Verify the integrity of a context chain.

    Returns::

        {
            "chain_intact": true,
            "length": 3,
            "root_hash": "sha256:...",
            "tip_hash": "sha256:..."
        }
    """
    return _req("GET", f"/api/verify/{ctx_id}")


def export(ctx_id: str) -> Dict:
    """
    Export a portable proof artifact for a context chain.
    Contains the full chain with integrity hashes suitable for external audit.
    """
    return _req("GET", f"/api/export/{ctx_id}")


def search(
    q: str = None,
    model: str = None,
    provider: str = None,
    event: str = None,
    trace_id: str = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 50,
) -> Dict:
    """
    Search your execution history.

    Example::

        results = dm.search(model="claude-opus-4-6", event="checkpoint")
        for ctx in results["results"]:
            print(ctx["id"], ctx["payload"])
    """
    params = []
    if q:         params.append(f"q={q}")
    if model:     params.append(f"model={model}")
    if provider:  params.append(f"provider={provider}")
    if event:     params.append(f"event={event}")
    if trace_id:  params.append(f"traceId={trace_id}")
    if from_date: params.append(f"from={from_date}")
    if to_date:   params.append(f"to={to_date}")
    if limit:     params.append(f"limit={limit}")
    qs = "?" + "&".join(params) if params else ""
    return _req("GET", f"/api/search{qs}")


def diff(ctx_id_a: str, ctx_id_b: str) -> Dict:
    """
    Diff two execution chains step-by-step.

    Useful for comparing:
    - Two runs of the same pipeline
    - An original run vs a fork
    - Same pipeline with different models

    Example::

        d = dm.diff(original_ctx_id, fork_ctx_id)
        print(f"{d['changedSteps']} steps changed")
        for step in d["steps"]:
            if step["diff"]["payloadChanged"]:
                print(f"Step {step['step']}: payload changed")
    """
    return _req("GET", f"/api/diff/{ctx_id_a}/{ctx_id_b}")


def me() -> Dict:
    """Return identity of the current agent."""
    return _req("GET", "/api/me")


# ── Class interface (for multi-agent / multi-key setups) ─────────────────────

class DarkMatter:
    """
    DarkMatter client with explicit API key and agent identity.

    Example::

        dm = DarkMatter(api_key="dm_sk_...", agent_id="my-agent")
        ctx = dm.commit("other-agent", payload={"output": result})
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or _get_key()
        self.base = base_url or _BASE

    def _req(self, method, path, body=None):
        return _req(method, path, body, key=self.api_key, base=self.base)

    def commit(self, to_agent_id, payload, parent_id=None, trace_id=None,
               branch_key=None, event_type="commit", agent=None):
        body = {"toAgentId": to_agent_id, "payload": payload, "eventType": event_type}
        if parent_id:  body["parentId"] = parent_id
        if trace_id:   body["traceId"] = trace_id
        if branch_key: body["branchKey"] = branch_key
        if agent:      body["agent"] = agent
        return self._req("POST", "/api/commit", body)

    def pull(self):
        return self._req("GET", "/api/pull")

    def replay(self, ctx_id, mode="full"):
        return self._req("GET", f"/api/replay/{ctx_id}?mode={mode}")

    def fork(self, ctx_id, to_agent_id=None, branch_key=None, payload=None):
        body = {}
        if to_agent_id: body["toAgentId"] = to_agent_id
        if branch_key:  body["branchKey"] = branch_key
        if payload:     body["payload"] = payload
        return self._req("POST", f"/api/fork/{ctx_id}", body)

    def verify(self, ctx_id):
        return self._req("GET", f"/api/verify/{ctx_id}")

    def export(self, ctx_id):
        return self._req("GET", f"/api/export/{ctx_id}")

    def search(self, q=None, model=None, provider=None, event=None,
               trace_id=None, from_date=None, to_date=None, limit=50):
        params = []
        if q:         params.append(f"q={q}")
        if model:     params.append(f"model={model}")
        if provider:  params.append(f"provider={provider}")
        if event:     params.append(f"event={event}")
        if trace_id:  params.append(f"traceId={trace_id}")
        if from_date: params.append(f"from={from_date}")
        if to_date:   params.append(f"to={to_date}")
        params.append(f"limit={limit}")
        return self._req("GET", f"/api/search?{'&'.join(params)}")

    def diff(self, ctx_id_a, ctx_id_b):
        return self._req("GET", f"/api/diff/{ctx_id_a}/{ctx_id_b}")

    def me(self):
        return self._req("GET", "/api/me")
