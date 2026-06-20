"""Ollama LLM client — async interface for local Ollama server.

Provides an ``async generate(prompt) -> str`` method compatible with
``RAGClassifier`` (which expects an LLM client with that signature).
"""

import logging

import aiohttp

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for local Ollama server.

    Args:
        base_url: Ollama API base URL (e.g. ``http://localhost:11434``)
        model: Model name (e.g. ``gemma4:e4b-it-qat-asst-think-64k``)
        temperature: LLM temperature (0 = deterministic)
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma4:e4b-it-qat-asst-think-64k",
        temperature: float = 0,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        """Generate a response from Ollama for the given prompt.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            The LLM's response as a string
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise RuntimeError(f"Ollama API error {resp.status}: {body[:200]}")
                    data = await resp.json()
                    response = data.get("response", "")
                    logger.debug("Ollama response: %d chars", len(response))
                    return response
        except aiohttp.ClientError as e:
            logger.error("Ollama connection error: %s", e)
            raise RuntimeError(f"Failed to connect to Ollama at {self.base_url}: {e}") from e

    def __repr__(self) -> str:
        return f"OllamaClient(model={self.model!r}, base_url={self.base_url!r})"
