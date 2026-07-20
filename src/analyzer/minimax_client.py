"""MiniMax LLM client — async interface for MiniMax API.

Provides an ``async generate(prompt) -> str`` method compatible with
``RAGClassifier`` (which expects an LLM client with that signature).
"""

import logging

import aiohttp

logger = logging.getLogger(__name__)


class MiniMaxClient:
    """Async client for MiniMax API.

    Args:
        api_key: MiniMax API token.
        base_url: MiniMax API base URL (e.g. ``https://api.minimax.io``).
        model: Model name (e.g. ``MiniMax-M3``).
        temperature: LLM temperature (0 = deterministic).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.minimax.io",
        model: str = "MiniMax-M3",
        temperature: float = 0,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        """Generate a response from MiniMax for the given prompt.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The LLM's response as a string.
        """
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "stream": False,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise RuntimeError(f"MiniMax API error {resp.status}: {body[:200]}")
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"] or ""
                    logger.debug("MiniMax response: %d chars", len(content))
                    return content
        except aiohttp.ClientError as e:
            logger.error("MiniMax connection error: %s", e)
            raise RuntimeError(f"Failed to connect to MiniMax API: {e}") from e

    def __repr__(self) -> str:
        return f"MiniMaxClient(model={self.model!r}, base_url={self.base_url!r})"
