# darkmatter

**Replay, fork, and verify any AI workflow.**

The execution record for AI agent pipelines. Works across any model, framework, or provider.

```bash
pip install darkmatter
darkmatter demo        # try it now — no signup required
```

## What it does

DarkMatter records every step of your AI pipeline as a cryptographically linked chain. You can then:

- **Replay** any workflow from root to tip, step by step
- **Fork** from any checkpoint to branch without losing the original
- **Verify** that a chain is intact and unmodified
- **Diff** two runs to see exactly what changed
- **Export** a portable proof artifact anyone can verify

Works with any model (Claude, GPT-4o, Gemini, local models) and any framework (LangGraph, LangChain, CrewAI, raw API calls).

## Quick start

```python
import darkmatter as dm
import os

os.environ["DARKMATTER_API_KEY"] = "dm_sk_..."  # get free key at darkmatterhub.ai/signup

# Commit agent output
ctx = dm.commit(
    to_agent_id="agent-writer-01",
    payload={
        "input":  "Analyze Q1 earnings",
        "output": {"summary": "APAC up 34%", "confidence": 0.94},
    },
    agent={"role": "researcher", "provider": "anthropic", "model": "claude-opus-4-6"},
)

# Chain commits by passing parent_id
ctx2 = dm.commit(
    to_agent_id="agent-reviewer-01",
    payload={"input": ctx["payload"]["output"], "output": "Approved."},
    parent_id=ctx["id"],
)

# Replay the full chain
replay = dm.replay(ctx2["id"])
print(f"{replay['totalSteps']} steps, chain intact: {replay['chainIntact']}")

# Verify integrity
result = dm.verify(ctx2["id"])
print(f"chain_intact: {result['chain_intact']}")
```

## LangGraph integration (one line)

```python
from langgraph.graph import StateGraph, END
from darkmatter.integrations.langgraph import DarkMatterTracer

# Your existing graph — unchanged
app = workflow.compile()

# Add DarkMatter — one line
app = DarkMatterTracer(app, agent_id="MY_AGENT_ID", to_agent_id="MY_AGENT_ID")

# Use exactly as before — every node auto-commits
result = app.invoke({"input": "Write a report"})
```

## Anthropic SDK integration

```python
import anthropic
from darkmatter.integrations.anthropic import dm_client

# Wrap your existing client — one line
client = dm_client(anthropic.Anthropic(), agent_id="agent-01", to_agent_id="agent-01")

# Use exactly as before — every call auto-commits
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Analyze Q1 earnings"}]
)
print(client.last_ctx_id)  # ctx_1234567890_abc123
```

## OpenAI SDK integration

```python
import openai
from darkmatter.integrations.openai import dm_client

client = dm_client(openai.OpenAI(), agent_id="agent-01", to_agent_id="agent-01")
response = client.chat.completions.create(model="gpt-4o", messages=[...])
print(client.last_ctx_id)
```

## Single agent / single developer

You do not need multiple agents. DarkMatter works for a single developer debugging their own pipeline:

```python
import darkmatter as dm

# Run your pipeline step by step
for i, step in enumerate(pipeline_steps):
    result = run_step(step)
    ctx = dm.commit(
        to_agent_id=MY_AGENT_ID,
        payload={"input": step, "output": result},
        parent_id=ctx["id"] if i > 0 else None,
    )

# Replay it
replay = dm.replay(ctx["id"])
for step in replay["replay"]:
    print(step["step"], step["payload"])
```

## Diff two runs

```python
# Run the same pipeline twice (or compare original vs fork)
d = dm.diff(run1_ctx_id, run2_ctx_id)
print(f"{d['changedSteps']} steps changed")
for step in d["steps"]:
    if step["diff"]["modelChanged"]:
        print(f"Step {step['step']}: {step['a']['model']} → {step['b']['model']}")
```

## Search your history

```python
# Find all checkpoints from claude on a specific trace
results = dm.search(model="claude-opus-4-6", event="checkpoint", trace_id="trc_abc")
for ctx in results["results"]:
    print(ctx["id"], ctx["payload"]["output"])
```

## API reference

| Function | Description |
|---|---|
| `dm.commit(to_agent_id, payload, ...)` | Commit context, returns Context Passport |
| `dm.pull()` | Pull contexts addressed to this agent |
| `dm.replay(ctx_id)` | Replay full chain root → tip |
| `dm.fork(ctx_id, ...)` | Fork from a checkpoint |
| `dm.verify(ctx_id)` | Verify chain integrity |
| `dm.export(ctx_id)` | Export portable proof artifact |
| `dm.search(q, model, ...)` | Search execution history |
| `dm.diff(ctx_id_a, ctx_id_b)` | Diff two chains step-by-step |
| `dm.me()` | Agent identity |

## Links

- [Documentation](https://darkmatterhub.ai/docs)
- [Live demo](https://darkmatterhub.ai/demo)
- [Get API key](https://darkmatterhub.ai/signup)
- [GitHub](https://github.com/bengunvl/darkmatter)
- [Context Passport spec](https://contextpassport.com)

## License

MIT
