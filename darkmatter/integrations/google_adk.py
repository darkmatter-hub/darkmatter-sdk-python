"""
DarkMatter Google ADK integration.

DarkMatterADKAgent: drop-in replacement for LlmAgent that auto-commits
every final response to DarkMatter.

DarkMatterADKRunner: wraps a Google ADK Runner to commit each turn of a
multi-turn session, building a full parent/child chain.

Usage — single agent::

    from darkmatter.integrations.google_adk import DarkMatterADKAgent
    import darkmatter as dm

    dm.configure(api_key="dm_sk_...", agent_id="dm_agent_...")
    agent = DarkMatterADKAgent(
        name="research_agent", model="gemini-2.0-flash",
        instruction="You are a research assistant.",
        to_agent_id="dm_agent_...", trace_id="trc_adk_001",
    )
    print(agent.last_ctx_id)  # ctx_...

Usage — multi-turn sessions::

    from darkmatter.integrations.google_adk import DarkMatterADKRunner
    from google.adk import Runner

    dm_runner = DarkMatterADKRunner(
        runner=Runner(agent=agent, app_name="my_app", session_service=session_svc),
        to_agent_id="dm_agent_...", trace_id="trc_session_001",
    )
    async for event in dm_runner.run_async(user_id="u1", session_id="s1", new_message=msg):
        pass  # each turn committed, full chain built

Requires: pip install google-adk>=0.4.0 darkmatter-sdk
"""

import time
import darkmatter as dm

try:
    from google.adk.agents import LlmAgent as _LlmAgent
    _HAS_ADK = True
except ImportError:
    _LlmAgent = object
    _HAS_ADK = False


def _extract_text(content) -> str:
    """Pull plain text from an ADK Content object or string."""
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    parts = getattr(content, 'parts', None) or []
    return ''.join(getattr(p, 'text', '') or '' for p in parts)


class DarkMatterADKAgent(_LlmAgent):
    """
    Drop-in replacement for google.adk.agents.LlmAgent.

    Every final response is auto-committed to DarkMatter.
    Constructor accepts all LlmAgent kwargs plus:
        to_agent_id: DarkMatter agent ID to receive the commits.
        trace_id:    Optional trace ID.
    """

    def __init__(self, name: str, model: str, instruction: str,
                 to_agent_id: str, trace_id: str = None, **kwargs):
        if not _HAS_ADK:
            raise ImportError(
                "google-adk not installed. Run: pip install 'google-adk>=0.4.0'"
            )
        super().__init__(name=name, model=model, instruction=instruction, **kwargs)
        self._dm_to_agent_id = to_agent_id
        self._dm_trace_id    = trace_id or f"trc_{int(time.time() * 1000)}"
        self._dm_parent_id   = None
        self.last_ctx_id     = None

    async def _run_async_impl(self, ctx):
        last_user_text = ''
        async for event in super()._run_async_impl(ctx):
            yield event
            if getattr(event, 'is_final_response', False):
                output_text = _extract_text(getattr(event, 'content', None))
                self._dm_commit(input_text=last_user_text, output_text=output_text)
            # Capture latest user input for the next final response
            author = getattr(event, 'author', None)
            if author == 'user':
                last_user_text = _extract_text(getattr(event, 'content', None))

    def _dm_commit(self, input_text: str, output_text: str):
        try:
            ctx = dm.commit(
                to_agent_id=self._dm_to_agent_id,
                payload={"input": input_text, "output": output_text},
                parent_id=self._dm_parent_id,
                trace_id=self._dm_trace_id,
                agent={"provider": "google-adk", "model": getattr(self, 'model', None)},
            )
            self._dm_parent_id = ctx.get("id")
            self.last_ctx_id   = ctx.get("id")
        except Exception as e:
            print(f"[DarkMatter] commit failed: {e}")


class DarkMatterADKRunner:
    """
    Wraps a Google ADK Runner to auto-commit each turn to DarkMatter.

    Builds a parent/child chain across turns so the full session is linked.

    Args:
        runner:       An instantiated google.adk.Runner.
        to_agent_id:  DarkMatter agent ID to receive the commits.
        trace_id:     Optional trace ID to group all turns from this session.
    """

    def __init__(self, runner, to_agent_id: str, trace_id: str = None):
        if not _HAS_ADK:
            raise ImportError(
                "google-adk not installed. Run: pip install 'google-adk>=0.4.0'"
            )
        self._runner       = runner
        self._to_agent_id  = to_agent_id
        self._trace_id     = trace_id or f"trc_{int(time.time() * 1000)}"
        self._parent_id    = None
        self.last_ctx_id   = None

    async def run_async(self, user_id: str, session_id: str, new_message):
        """
        Async generator mirroring Runner.run_async().

        Yields all events unchanged and commits to DarkMatter on each final response.
        """
        input_text = _extract_text(
            getattr(new_message, 'parts', None) and new_message or None
        ) or getattr(new_message, 'text', str(new_message))

        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            yield event

            is_final = (
                getattr(event, 'is_final_response', False)
                or getattr(event, 'turn_complete', False)
            )
            if is_final:
                output_text = _extract_text(getattr(event, 'content', None))
                try:
                    ctx = dm.commit(
                        to_agent_id=self._to_agent_id,
                        payload={"input": input_text, "output": output_text},
                        parent_id=self._parent_id,
                        trace_id=self._trace_id,
                    )
                    self._parent_id = ctx.get("id")
                    self.last_ctx_id = ctx.get("id")
                except Exception as e:
                    print(f"[DarkMatter] commit failed: {e}")

    def __getattr__(self, name):
        """Proxy everything else to the underlying runner."""
        return getattr(self._runner, name)
