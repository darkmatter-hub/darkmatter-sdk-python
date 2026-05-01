"""
DarkMatter CrewAI integration.

Hooks into CrewAI's event bus to auto-commit a Context Passport after every
task completion. Zero changes to your agents, tasks, or crew definition.

Usage::

    from darkmatter.integrations.crewai import observe_crew
    import darkmatter as dm

    dm.configure(api_key="dm_sk_...", agent_id="dm_agent_...")
    observer = observe_crew(to_agent_id="dm_agent_...", trace_id="trc_001")

    crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
    crew.kickoff()

    print(observer.last_ctx_id)  # ctx_...

Requires: pip install 'crewai>=0.60.0' darkmatter-sdk
"""

import time
import darkmatter as dm


class DarkMatterObserver:
    """
    Listens for CrewAI TaskCompletedEvents and commits each one to DarkMatter.

    Builds a parent/child chain across tasks automatically.
    Never raises — DarkMatter failures are printed and swallowed.
    """

    def __init__(self, to_agent_id: str, trace_id: str = None):
        self._to_agent_id = to_agent_id
        self._trace_id = trace_id or f"trc_{int(time.time() * 1000)}"
        self._parent_id = None
        self.last_ctx_id = None

    def _commit(self, task_input: str, task_output: str, agent_role: str = None, agent_model: str = None):
        try:
            agent_info = None
            if agent_role or agent_model:
                agent_info = {"role": agent_role, "model": agent_model}
            ctx = dm.commit(
                to_agent_id=self._to_agent_id,
                payload={"input": task_input, "output": task_output},
                parent_id=self._parent_id,
                trace_id=self._trace_id,
                agent=agent_info,
            )
            self._parent_id = ctx.get("id")
            self.last_ctx_id = ctx.get("id")
        except Exception as e:
            print(f"[DarkMatter] commit failed: {e}")


def observe_crew(to_agent_id: str, trace_id: str = None) -> DarkMatterObserver:
    """
    Register a DarkMatter observer on the CrewAI event bus.

    Call once before crew.kickoff(). Every task completion is automatically
    committed to DarkMatter as a chained Context Passport.

    Args:
        to_agent_id: DarkMatter agent ID to receive the commits.
        trace_id:    Optional trace ID to group all task commits from this run.

    Returns:
        DarkMatterObserver with a .last_ctx_id attribute updated after each task.
    """
    observer = DarkMatterObserver(to_agent_id=to_agent_id, trace_id=trace_id)

    try:
        from crewai.utilities.events import crewai_event_bus
        from crewai.utilities.events.task_events import TaskCompletedEvent

        @crewai_event_bus.on(TaskCompletedEvent)
        def _on_task_completed(source, event):
            agent = getattr(source, 'agent', None)
            role = getattr(agent, 'role', None)
            model = str(getattr(agent, 'llm', '') or '')

            task = getattr(event, 'task', None) or source
            description = getattr(task, 'description', '') or ''
            output = getattr(event, 'output', None)
            output_str = getattr(output, 'raw', None) or str(output or '')

            observer._commit(
                task_input=description,
                task_output=output_str,
                agent_role=role,
                agent_model=model or None,
            )

    except ImportError:
        print(
            "[DarkMatter] crewai event bus not found — upgrade to crewai>=0.60.0 "
            "or pass observer._commit as task_callback manually."
        )

    return observer
