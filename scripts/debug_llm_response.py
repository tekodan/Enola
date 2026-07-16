"""Debug helper: dump the raw LLM response for a given text to a file.

Usage:
    .venv/bin/python scripts/debug_llm_response.py "texto a clasificar" --out /tmp/llm_raw.txt
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="Text to classify")
    parser.add_argument("--out", type=Path, default=Path("/tmp/llm_raw.txt"))
    args = parser.parse_args()

    from src.analyzer.few_shot_loader import load_few_shot_examples
    from src.analyzer.llm_client import OllamaClient
    from src.analyzer.rag_classifier import RAGClassifier
    from src.config.settings import get_settings

    settings = get_settings()
    llm = OllamaClient(
        base_url=settings.ollama.base_url,
        model=settings.ollama.llm_model,
        temperature=0,
        max_tokens=settings.analyzer.max_tokens,
    )
    clf = RAGClassifier(
        llm_client=llm,
        few_shot_examples=list(load_few_shot_examples()),
        context_chunks=0,
        feedback_store=None,
    )

    # Get the prompt that would be sent
    prompt = clf._build_prompt(args.text, context_chunks=[])
    print(f"Prompt length: {len(prompt)} chars", file=sys.stderr)

    # Call the LLM directly
    raw = await llm.generate(prompt)
    args.out.write_text(raw, encoding="utf-8")
    print(f"Raw response ({len(raw)} chars) written to {args.out}", file=sys.stderr)
    print(f"\nFirst 200 chars:\n{raw[:200]!r}", file=sys.stderr)
    print(f"\nLast 200 chars:\n{raw[-200:]!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
