#!/usr/bin/env python3
"""
darkmatter CLI
pip install darkmatter && darkmatter demo
"""

import sys
import os
import json
import time
import hashlib
import secrets
import webbrowser
from datetime import datetime, timezone


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _make_local_ctx(agent_id, agent_name, role, payload, parent=None,
                    model="local", provider="local", event_type="commit"):
    """Build a Context Passport locally without any network call."""
    ts = str(int(time.time() * 1000))
    ctx_id = f"ctx_{ts}_{secrets.token_hex(6)}"
    now = datetime.now(timezone.utc).isoformat()

    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    payload_hash = _sha256(canonical)
    parent_hash = parent["integrity"]["_raw_integrity_hash"] if parent else None
    chain_input = payload_hash + (parent_hash or "root")
    integrity_hash = _sha256(chain_input)

    return {
        "id":             ctx_id,
        "schema_version": "1.0",
        "parent_id":      parent["id"] if parent else None,
        "trace_id":       f"trc_demo_{ts}",
        "branch_key":     "main",
        "created_by": {
            "agent_id":   agent_id,
            "agent_name": agent_name,
            "role":       role,
            "provider":   provider,
            "model":      model,
        },
        "event": {
            "type":      event_type,
            "timestamp": now,
        },
        "payload": payload,
        "integrity": {
            "payload_hash":        f"sha256:{payload_hash}",
            "parent_hash":         f"sha256:{parent_hash}" if parent_hash else None,
            "integrity_hash":      f"sha256:{integrity_hash}",
            "verification_status": "valid",
            "_raw_integrity_hash": integrity_hash,  # internal, stripped in display
        },
        "created_at": now,
    }


def _verify_chain(chain):
    prev = None
    for ctx in chain:
        canonical = json.dumps(ctx["payload"], sort_keys=True, separators=(',', ':'))
        ph = _sha256(canonical)
        parent_hash = prev["integrity"]["_raw_integrity_hash"] if prev else None
        chain_input = ph + (parent_hash or "root")
        expected = _sha256(chain_input)
        actual = ctx["integrity"]["integrity_hash"].replace("sha256:", "")
        if actual != expected:
            return False
        prev = ctx
    return True


def _print_ctx(ctx, step, total):
    from_short = ctx["id"][-8:]
    role = ctx["created_by"]["role"]
    ih = ctx["integrity"]["integrity_hash"][:18] + "..."
    parent = ctx["parent_id"][-8:] if ctx["parent_id"] else "root"
    print(f"  Step {step}/{total}  [{role}]  {ctx['id'][-20:]}")
    print(f"           parent: {parent}  integrity: {ih}")


def demo():
    """
    darkmatter demo — runs locally, no signup required.

    Creates a 3-step agent chain, verifies integrity,
    and shows you what DarkMatter stores.
    """
    W  = "\033[0m"
    B  = "\033[1m"
    V  = "\033[35m"
    G  = "\033[32m"
    C  = "\033[36m"
    Y  = "\033[33m"
    R  = "\033[31m"
    DIM = "\033[2m"

    print()
    print(f"{B}{V}DarkMatter{W} — execution record for AI agent pipelines")
    print(f"{DIM}replay · fork · verify — any workflow, any model{W}")
    print()
    print(f"{DIM}Running local demo (no API key required){W}")
    print()

    time.sleep(0.3)

    # ── Step 1: Research agent ────────────────────────────────────────────────
    print(f"{C}●{W} Step 1/3  Researcher agent commits context...")
    time.sleep(0.4)

    ctx1 = _make_local_ctx(
        agent_id="agent-researcher-demo",
        agent_name="Research Agent",
        role="researcher",
        provider="anthropic",
        model="claude-opus-4-6",
        payload={
            "input":  "Analyze Q1 2026 earnings across APAC region",
            "output": {
                "summary":    "APAC revenue up 34% YoY, driven by Japan and South Korea",
                "confidence": 0.94,
                "sources":    ["q1_report.pdf", "analyst_call_transcript.txt"],
                "key_risk":   "Currency headwinds in Q2",
            },
            "memory": {"temperature": 0.3, "max_tokens": 2048},
        },
        event_type="commit",
    )
    print(f"  {G}✓{W} Committed  {DIM}{ctx1['id']}{W}")
    print(f"    payload_hash: {DIM}{ctx1['integrity']['payload_hash'][:32]}...{W}")
    time.sleep(0.4)

    # ── Step 2: Writer agent ──────────────────────────────────────────────────
    print(f"\n{C}●{W} Step 2/3  Writer agent receives context and commits...")
    time.sleep(0.4)

    ctx2 = _make_local_ctx(
        agent_id="agent-writer-demo",
        agent_name="Writer Agent",
        role="writer",
        provider="openai",
        model="gpt-4o",
        payload={
            "input":  ctx1["payload"]["output"],
            "output": "Q1 APAC Performance Report: Strong growth signals despite macro headwinds...",
            "memory": {"word_count": 847, "tone": "executive"},
        },
        parent=ctx1,
        event_type="commit",
    )
    print(f"  {G}✓{W} Committed  {DIM}{ctx2['id']}{W}")
    print(f"    parent_hash:  {DIM}{ctx2['integrity']['parent_hash'][:32]}...{W}")
    time.sleep(0.4)

    # ── Step 3: Reviewer agent ────────────────────────────────────────────────
    print(f"\n{C}●{W} Step 3/3  Reviewer agent checkpoints...")
    time.sleep(0.4)

    ctx3 = _make_local_ctx(
        agent_id="agent-reviewer-demo",
        agent_name="Review Agent",
        role="reviewer",
        provider="anthropic",
        model="claude-opus-4-6",
        payload={
            "input":    ctx2["payload"]["output"],
            "output":   "Approved. Minor edit: soften Q2 risk language.",
            "memory":   {"decision": "approved", "edit_count": 1},
            "variables": {"approved": True, "send_to": "cfo@company.com"},
        },
        parent=ctx2,
        event_type="checkpoint",
    )
    print(f"  {G}✓{W} Committed  {DIM}{ctx3['id']}{W}")
    time.sleep(0.3)

    chain = [ctx1, ctx2, ctx3]

    # ── Verify ────────────────────────────────────────────────────────────────
    print(f"\n{B}Verifying integrity chain...{W}")
    time.sleep(0.5)
    intact = _verify_chain(chain)
    if intact:
        print(f"  {G}✓ Chain intact{W}  root→tip  3 commits  cryptographically linked")
    else:
        print(f"  {R}✗ Chain broken{W}")

    # ── Replay ────────────────────────────────────────────────────────────────
    print(f"\n{B}Replay (root → tip):{W}")
    time.sleep(0.3)
    for i, ctx in enumerate(chain, 1):
        role     = ctx["created_by"]["role"]
        model    = ctx["created_by"]["model"]
        provider = ctx["created_by"]["provider"]
        parent   = ctx["parent_id"][-8:] if ctx["parent_id"] else "root"
        print(f"  {i}. {B}{role}{W}  {DIM}({provider} / {model}){W}")
        print(f"     id: {ctx['id'][-20:]}  parent: {parent}")
    time.sleep(0.3)

    # ── Fork demo ─────────────────────────────────────────────────────────────
    print(f"\n{B}Forking from step 2 (try gpt-4o instead of claude for review)...{W}")
    time.sleep(0.4)
    fork_ctx = _make_local_ctx(
        agent_id="agent-reviewer-demo",
        agent_name="Review Agent (fork)",
        role="reviewer",
        provider="openai",
        model="gpt-4o",
        payload={
            "input":    ctx2["payload"]["output"],
            "output":   "Approved. No edits needed. Strong report.",
            "memory":   {"decision": "approved", "edit_count": 0},
            "variables": {"approved": True},
        },
        parent=ctx2,
        event_type="fork",
    )
    print(f"  {Y}⑂{W} Fork created  {DIM}{fork_ctx['id']}{W}")
    print(f"    branch_key: fork-{fork_ctx['id'][-6:]}")

    # ── Diff ──────────────────────────────────────────────────────────────────
    print(f"\n{B}Diff: original review vs fork review{W}")
    time.sleep(0.3)
    orig_output = ctx3["payload"]["output"]
    fork_output = fork_ctx["payload"]["output"]
    orig_model  = ctx3["created_by"]["model"]
    fork_model  = fork_ctx["created_by"]["model"]
    print(f"  model:   {R}{orig_model}{W} → {G}{fork_model}{W}")
    print(f"  output:  {R}\"{orig_output[:40]}...\"{W}")
    print(f"           {G}\"{fork_output[:40]}\"{W}")
    print(f"  edit_count: {R}1{W} → {G}0{W}")

    # ── Export ────────────────────────────────────────────────────────────────
    print(f"\n{B}Export (portable proof artifact):{W}")
    time.sleep(0.3)
    export_hash = _sha256(json.dumps([c["integrity"]["integrity_hash"] for c in chain]))
    print(f"  chain_hash:  sha256:{export_hash[:40]}...")
    print(f"  chain_length: 3 commits")
    print(f"  chain_intact: {G}true{W}")
    print(f"  {DIM}This artifact can be verified by anyone with the chain —{W}")
    print(f"  {DIM}no access to DarkMatter required.{W}")

    # ── What to do next ───────────────────────────────────────────────────────
    print()
    print(f"{'─'*56}")
    print(f"{B}What just happened:{W}")
    print(f"  3 agents committed context as a cryptographic chain.")
    print(f"  Each commit links to its parent via SHA-256 hash.")
    print(f"  The chain is tamper-evident: modify any step,")
    print(f"  every downstream hash breaks.")
    print()
    print(f"{B}Next steps:{W}")
    print(f"  1. Get a free API key:  {C}https://darkmatterhub.ai/signup{W}")
    print(f"  2. Set it:              {DIM}export DARKMATTER_API_KEY=dm_sk_...{W}")
    print(f"  3. Add to your pipeline:")
    print()
    print(f"  {DIM}import darkmatter as dm{W}")
    print(f"  {DIM}ctx = dm.commit(to_agent_id, payload={{\"output\": result}}){W}")
    print()
    print(f"  {B}LangGraph (1 line):{W}")
    print(f"  {DIM}from darkmatter.integrations.langgraph import DarkMatterTracer{W}")
    print(f"  {DIM}app = DarkMatterTracer(app, agent_id=ID, to_agent_id=ID){W}")
    print()
    print(f"  Full docs:  {C}https://darkmatterhub.ai/docs{W}")
    print(f"  Live demo:  {C}https://darkmatterhub.ai/demo{W}")
    print()


def main():
    args = sys.argv[1:]

    if not args or args[0] == "demo":
        demo()
        return

    if args[0] in ("--help", "-h", "help"):
        print("DarkMatter CLI")
        print()
        print("Commands:")
        print("  darkmatter demo     Run local demo (no signup required)")
        print("  darkmatter --help   Show this help")
        print()
        print("Environment:")
        print("  DARKMATTER_API_KEY  Your DarkMatter API key")
        print()
        print("Get started: https://darkmatterhub.ai/signup")
        return

    if args[0] in ("--version", "-v", "version"):
        from darkmatter import __version__
        print(f"darkmatter {__version__}")
        return

    print(f"Unknown command: {args[0]}")
    print("Run 'darkmatter --help' for usage.")
    sys.exit(1)


if __name__ == "__main__":
    main()
