"""
DarkMatter OpenAI SDK integration.

Usage::

    import openai
    from darkmatter.integrations.openai import dm_client

    client = dm_client(openai.OpenAI(), agent_id="MY_AGENT_ID", to_agent_id="MY_AGENT_ID")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarize Q1 earnings"}]
    )
    print(client.last_ctx_id)
"""

from darkmatter.client import DarkMatter


class _TrackedCompletions:
    def __init__(self, completions, dm, agent_id, to_agent_id, tracker, trace_id=None):
        self._completions = completions
        self._dm = dm
        self._agent_id = agent_id
        self._to_agent_id = to_agent_id
        self._tracker = tracker
        self._trace_id = trace_id

    def create(self, **kwargs):
        response = self._completions.create(**kwargs)
        output = ""
        try:
            output = response.choices[0].message.content or ""
        except Exception:
            pass
        model = kwargs.get("model", "")
        try:
            ctx = self._dm.commit(
                to_agent_id=self._to_agent_id,
                payload={
                    "input":  kwargs.get("messages", []),
                    "output": output,
                    "memory": {
                        "model":          model,
                        "finish_reason":  getattr(getattr(response, "choices", [None])[0], "finish_reason", None),
                        "usage":          {
                            "prompt_tokens":     getattr(getattr(response, "usage", None), "prompt_tokens", None),
                            "completion_tokens": getattr(getattr(response, "usage", None), "completion_tokens", None),
                        },
                    },
                },
                parent_id=self._tracker.get("last_ctx_id"),
                trace_id=self._trace_id,
                event_type="commit",
                agent={"provider": "openai", "model": model},
            )
            self._tracker["last_ctx_id"] = ctx.get("id")
        except Exception as e:
            print(f"[DarkMatter] commit failed: {e}")
        return response

    def __getattr__(self, name):
        return getattr(self._completions, name)


class _TrackedChat:
    def __init__(self, chat, dm, agent_id, to_agent_id, tracker, trace_id=None):
        self.completions = _TrackedCompletions(
            chat.completions, dm, agent_id, to_agent_id, tracker, trace_id
        )
    def __getattr__(self, name):
        return getattr(self._chat, name)


class _TrackedOpenAIClient:
    def __init__(self, client, dm, agent_id, to_agent_id, trace_id=None):
        self._client = client
        self._tracker = {"last_ctx_id": None}
        self.chat = _TrackedChat(client.chat, dm, agent_id, to_agent_id, self._tracker, trace_id)

    @property
    def last_ctx_id(self):
        return self._tracker["last_ctx_id"]

    def __getattr__(self, name):
        return getattr(self._client, name)


def dm_client(openai_client, agent_id: str, to_agent_id: str,
               api_key: str = None, trace_id: str = None):
    """Wrap an OpenAI client to automatically commit Context Passports."""
    dm = DarkMatter(api_key=api_key)
    return _TrackedOpenAIClient(openai_client, dm, agent_id, to_agent_id, trace_id)
