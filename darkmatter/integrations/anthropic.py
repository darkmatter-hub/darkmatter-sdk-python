"""
DarkMatter Anthropic SDK integration.

Wraps the Anthropic client so every messages.create() call
automatically commits a Context Passport.

Usage::

    import anthropic
    from darkmatter.integrations.anthropic import dm_client

    client = dm_client(
        anthropic.Anthropic(),
        agent_id="MY_AGENT_ID",
        to_agent_id="MY_AGENT_ID",
    )

    # Use exactly like the normal Anthropic client
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Analyze Q1 earnings"}]
    )
    # Automatically committed to DarkMatter
    print(client.last_ctx_id)  # ctx_1234567890_abc123
"""

from darkmatter.client import DarkMatter


class _TrackedMessages:
    def __init__(self, messages, dm: DarkMatter, agent_id: str, to_agent_id: str,
                 parent_tracker, trace_id: str = None):
        self._messages = messages
        self._dm = dm
        self._agent_id = agent_id
        self._to_agent_id = to_agent_id
        self._parent_tracker = parent_tracker
        self._trace_id = trace_id

    def create(self, **kwargs):
        response = self._messages.create(**kwargs)

        # Extract text output
        output_text = ""
        if hasattr(response, "content") and response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    output_text += block.text

        # Extract input messages
        input_messages = kwargs.get("messages", [])
        model = kwargs.get("model", "")

        try:
            ctx = self._dm.commit(
                to_agent_id=self._to_agent_id,
                payload={
                    "input":  input_messages,
                    "output": output_text,
                    "memory": {
                        "model":       model,
                        "stop_reason": getattr(response, "stop_reason", None),
                        "usage":       {
                            "input_tokens":  getattr(getattr(response, "usage", None), "input_tokens", None),
                            "output_tokens": getattr(getattr(response, "usage", None), "output_tokens", None),
                        },
                    },
                },
                parent_id=self._parent_tracker.get("last_ctx_id"),
                trace_id=self._trace_id,
                event_type="commit",
                agent={
                    "provider": "anthropic",
                    "model":    model,
                },
            )
            self._parent_tracker["last_ctx_id"] = ctx.get("id")
        except Exception as e:
            print(f"[DarkMatter] commit failed: {e}")

        return response

    def __getattr__(self, name):
        return getattr(self._messages, name)


class _TrackedClient:
    def __init__(self, client, dm: DarkMatter, agent_id: str, to_agent_id: str,
                 trace_id: str = None):
        self._client = client
        self._tracker = {"last_ctx_id": None}
        self.messages = _TrackedMessages(
            client.messages, dm, agent_id, to_agent_id, self._tracker, trace_id
        )

    @property
    def last_ctx_id(self):
        return self._tracker["last_ctx_id"]

    def __getattr__(self, name):
        return getattr(self._client, name)


def dm_client(anthropic_client, agent_id: str, to_agent_id: str,
               api_key: str = None, trace_id: str = None) -> _TrackedClient:
    """
    Wrap an Anthropic client to automatically commit Context Passports.

    Args:
        anthropic_client: An instantiated anthropic.Anthropic() client
        agent_id:         Your DarkMatter agent ID
        to_agent_id:      Recipient agent ID (can be same as agent_id)
        api_key:          DarkMatter API key (defaults to DARKMATTER_API_KEY)
        trace_id:         Optional trace ID to group all calls in a session

    Returns:
        A wrapped client with identical interface to anthropic.Anthropic()

    Example::

        import anthropic
        from darkmatter.integrations.anthropic import dm_client

        client = dm_client(anthropic.Anthropic(), "agent-01", "agent-01")
        resp = client.messages.create(model="claude-opus-4-6", max_tokens=512,
                                      messages=[{"role": "user", "content": "Hello"}])
        print(client.last_ctx_id)
    """
    dm = DarkMatter(api_key=api_key)
    return _TrackedClient(anthropic_client, dm, agent_id, to_agent_id, trace_id)
