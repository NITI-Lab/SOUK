"""AgentCore Lambda / API Gateway target adapter.

Connects to an AgentCore-style agent via its REST API.
"""

from __future__ import annotations

import time
import uuid

import httpx

from souk.config import TargetConfig


class AgentCoreTarget:
    """Target adapter for an AgentCore API Gateway endpoint.

    Config example (in config.yaml):
        target:
          provider: agentcore
          base_url: https://example.execute-api.us-west-2.amazonaws.com/prod/agentcore
          api_key: your-api-key
          extra:
            tenant_id: default
            model_id: anthropic.claude-haiku-4-5-20251001-v1:0  # optional
            timeout: 90
    """

    def __init__(self, config: TargetConfig) -> None:
        self.config = config
        self.base_url = config.base_url
        if not self.base_url:
            raise ValueError("AgentCoreTarget requires base_url")
        self.api_key = config.resolve_api_key() or ""
        self.tenant_id = config.extra.get("tenant_id", "default")
        self.model_id = config.extra.get("model_id")
        self.timeout = config.extra.get("timeout", 90)

    async def run_conversation(
        self,
        user_turns: list[str],
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Send user turns to the AgentCore endpoint and collect responses."""
        session_id = f"souk-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        conversation: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for user_msg in user_turns:
                payload = {
                    "action": "invoke",
                    "session_id": session_id,
                    "tenant_id": self.tenant_id,
                    "message": user_msg,
                }
                if self.model_id:
                    payload["model_id"] = self.model_id

                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                }

                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                assistant_msg = data.get("response", "")
                conversation.append({"role": "user", "content": user_msg})
                conversation.append({"role": "assistant", "content": assistant_msg})

            try:
                await client.post(
                    self.base_url,
                    json={
                        "action": "reset_session",
                        "session_id": session_id,
                        "tenant_id": self.tenant_id,
                    },
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                    },
                )
            except Exception:
                pass

        return conversation
