"""
DarkMatter AWS Bedrock integration.

Wraps the boto3 Bedrock runtime client so every invoke_model() and
invoke_agent() call auto-commits a Context Passport.

Usage::

    from darkmatter.integrations.bedrock import DarkMatterBedrockClient
    import darkmatter as dm

    dm.configure(api_key="dm_sk_...", agent_id="dm_agent_...")

    bedrock = DarkMatterBedrockClient(
        region="us-east-1", to_agent_id="dm_agent_...", trace_id="trc_001"
    )
    result = bedrock.invoke_model(
        model_id="anthropic.claude-opus-4-6-v1:0",
        prompt="Analyze this contract for risk clauses",
    )
    print(bedrock.last_ctx_id)  # ctx_...

Requires: pip install boto3 darkmatter-sdk
AWS credentials via environment or IAM role.
"""

import json
import time
import darkmatter as dm


class DarkMatterBedrockClient:
    """
    Wraps boto3 bedrock-runtime and bedrock-agent-runtime clients.

    Every invoke_model() and invoke_agent() call is auto-committed to DarkMatter.
    Never raises due to DarkMatter failures — errors are printed and swallowed.

    Args:
        region:       AWS region (e.g. "us-east-1").
        to_agent_id:  DarkMatter agent ID to receive the commits.
        trace_id:     Optional trace ID to group all calls from this session.
        api_key:      DarkMatter API key (defaults to DARKMATTER_API_KEY env var).
    """

    def __init__(self, region: str, to_agent_id: str, trace_id: str = None, api_key: str = None):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 not installed. Run: pip install boto3")

        self._runtime = boto3.client('bedrock-runtime', region_name=region)
        self._agents  = boto3.client('bedrock-agent-runtime', region_name=region)
        self._to_agent_id = to_agent_id
        self._trace_id    = trace_id or f"trc_{int(time.time() * 1000)}"
        self._parent_id   = None
        self.last_ctx_id  = None

    def invoke_model(self, model_id: str, prompt: str, **kwargs) -> dict:
        """
        Invoke a Bedrock foundation model and auto-commit the result.

        Args:
            model_id: Bedrock model ID (e.g. "anthropic.claude-opus-4-6-v1:0").
            prompt:   Prompt string to send to the model.
            **kwargs: Additional fields merged into the request body.

        Returns:
            Parsed JSON response from the model.
        """
        body = json.dumps({"prompt": prompt, **kwargs})
        start = time.time()
        response = self._runtime.invoke_model(
            modelId=model_id,
            body=body,
            contentType='application/json',
            accept='application/json',
        )
        latency = time.time() - start
        output = json.loads(response['body'].read())

        self._record(
            input_text=prompt,
            output=output,
            model=model_id,
            provider='bedrock',
            latency=latency,
        )
        return output

    def invoke_agent(self, agent_id: str, agent_alias: str, session_id: str, prompt: str) -> str:
        """
        Invoke a Bedrock Agent and auto-commit the full response.

        Args:
            agent_id:     Bedrock Agent ID (e.g. "ABCDEF1234").
            agent_alias:  Agent alias ID (e.g. "TSTALIASID").
            session_id:   Session identifier for multi-turn conversations.
            prompt:       User message.

        Returns:
            Agent response text.
        """
        start = time.time()
        response = self._agents.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias,
            sessionId=session_id,
            inputText=prompt,
        )
        latency = time.time() - start

        parts = []
        for event in response.get('completion', []):
            if 'chunk' in event:
                parts.append(event['chunk'].get('bytes', b'').decode('utf-8', errors='replace'))
        output_text = ''.join(parts)

        self._record(
            input_text=prompt,
            output=output_text,
            model=f"{agent_id}/{agent_alias}",
            provider='bedrock-agents',
            latency=latency,
            extra={"session_id": session_id},
        )
        return output_text

    def _record(self, input_text, output, model, provider, latency=None, extra=None):
        try:
            payload = {"input": input_text, "output": output}
            if extra:
                payload["memory"] = extra
            if latency is not None:
                payload.setdefault("memory", {})
                payload["memory"]["latency_ms"] = round(latency * 1000)

            ctx = dm.commit(
                to_agent_id=self._to_agent_id,
                payload=payload,
                parent_id=self._parent_id,
                trace_id=self._trace_id,
                agent={"provider": provider, "model": model},
            )
            self._parent_id = ctx.get("id")
            self.last_ctx_id = ctx.get("id")
        except Exception as e:
            print(f"[DarkMatter] commit failed: {e}")
