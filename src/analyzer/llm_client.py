"""Ollama LLM client — async interface for local Ollama server.

Provides an ``async generate(prompt) -> str`` method compatible with
``RAGClassifier`` (which expects an LLM client with that signature).

Uses Ollama's **native** API (``/api/generate``). The ``think`` field
is the native wire format for the reasoning-trace channel. Verified
behavior on the local Ollama (curl tests 2026-07-15):

  - ``think=True``: reasoning models emit their chain-of-thought in
    the ``thinking`` field; ``response`` stays clean. **Default here**
    because it never embeds ``<think>`` tags in ``response`` — the
    JSON parser never sees them.
  - ``think=False``: with thinking-capable variants
    (e.g. ``gemma4:e2b-it-qat-asst-think-32k``) the model **still
    reasons** and dumps ``<think>...</think>`` inside ``response``
    (breaks the JSON parser). Only models that don't reason by
    default (``gemma4:26b-a4b-it-qat-raw-default-64k``) behave
    identically with or without the field.
  - The OpenAI-compat format ``reasoning: { effort: "none" }`` is
    translated server-side (``openai/openai.go``) into the same
    ``think`` value, so it's equivalent on the wire — but irrelevant
    here because we hit the native endpoint with ``aiohttp``.

The real lever for "fast / no reasoning" is the **model variant**:
pick a non-reasoning checkpoint (``raw-default-64k`` or any model
whose ``capabilities`` doesn't include ``thinking``). The ``think``
field only controls trace *format*, not whether the model reasons.
"""

import logging

import aiohttp

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for local Ollama server.

    Args:
        base_url: Ollama API base URL (e.g. ``http://localhost:11434``)
        model: Model name. Default
            ``gemma4:26b-a4b-it-qat-raw-default-64k`` is the
            non-reasoning variant verified to emit a clean response
            (no ``<think>`` tags, ``thinking`` field empty). The
            assistant-tuned ``asst-think-64k`` checkpoints spend
            ~12k chars on internal thinking and stop before producing
            the visible JSON when ``num_predict < 6000`` — avoid them
            for batch classification.
        temperature: LLM temperature (0 = deterministic)
        timeout: Request timeout in seconds
        max_tokens: Optional ``num_predict`` cap on output tokens
        think: Wire-level ``think`` field. ``True`` (default) routes
            any reasoning trace to a separate channel so ``response``
            stays clean; ``False`` is a no-op for non-reasoning models
            but breaks JSON parsing on reasoning-capable ones.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma4:26b-a4b-it-qat-raw-default-64k",
        temperature: float = 0,
        timeout: int = 120,
        max_tokens: int | None = None,
        think: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.think = think

    async def generate(self, prompt: str) -> str:
        """Generate a response from Ollama for the given prompt.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            The LLM's response as a string
        """
        url = f"{self.base_url}/api/generate"
        options: dict[str, object] = {
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            options["num_predict"] = self.max_tokens
        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
            "options": options,
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
