"""Synthetic query generation for the D1 golden set (R-04a, R-C).

Each tool gets 3–5 paraphrased intents. The R-C guard rejects any candidate
that names the tool verbatim and regenerates. Generation is behind a
``QueryGenerator`` Protocol so CI injects a deterministic fake and the live path
uses the Anthropic SDK. Hard negatives (R-04b) are human-added, not generated.
"""

from __future__ import annotations

import re
from typing import Protocol

from .models import CorpusTool, GoldenSet, Label, Query

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


class QueryGenerator(Protocol):
    def generate(self, tool: CorpusTool, n: int) -> list[str]: ...


def names_tool(query: str, tool: CorpusTool) -> bool:
    """R-C: True when the query names the tool (verbatim, case-insensitive).

    Matches the tool name as a whole token, and the ``server:tool`` id as a
    substring (e.g. ``github:create_issue``).
    """
    lowered = query.lower()
    if tool.tool_id.lower() in lowered:
        return True
    tokens = set(_TOKEN_RE.findall(lowered))
    return tool.tool.lower() in tokens


def generate_queries(
    corpus,
    generator: QueryGenerator,
    *,
    per_tool: int = 3,
    max_attempts_factor: int = 5,
) -> GoldenSet:
    """Generate ``per_tool`` R-C-clean paraphrased queries per corpus tool."""
    queries: list[Query] = []
    counter = 0
    for tool in corpus.tools:
        accepted: list[str] = []
        attempts = 0
        budget = per_tool * max_attempts_factor
        while len(accepted) < per_tool and attempts < budget:
            need = per_tool - len(accepted)
            candidates = generator.generate(tool, need)
            if not candidates:
                break
            for cand in candidates:
                attempts += 1
                cand = cand.strip()
                if not cand or names_tool(cand, tool):
                    continue  # R-C reject -> regenerate
                if cand in accepted:
                    continue
                accepted.append(cand)
                if len(accepted) >= per_tool:
                    break
        for text in accepted:
            counter += 1
            queries.append(
                Query(
                    id=f"q{counter:04d}",
                    query=text,
                    labels=[Label(tool_id=tool.tool_id, relevance=2)],
                )
            )
    return GoldenSet(corpus_version=corpus.version, queries=queries)


class AnthropicQueryGenerator:
    """Live generator using the Anthropic SDK (not exercised in CI).

    Asks the model for paraphrased user intents that must NOT mention the tool
    name (R-C is still enforced downstream in :func:`generate_queries`).
    """

    def __init__(self, client=None, model: str = "claude-sonnet-4-6"):
        self._client = client
        self._model = model

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # local import: keeps the dep optional in tests

            self._client = anthropic.Anthropic()
        return self._client

    def generate(self, tool: CorpusTool, n: int) -> list[str]:
        client = self._ensure_client()
        prompt = (
            f"A tool does the following:\n{tool.description}\n\n"
            f"Write {n} short, natural user requests that this tool would satisfy. "
            "Each must paraphrase the INTENT only. Never mention the tool's name "
            f"('{tool.tool}') or any server/tool identifier. One request per line."
        )
        msg = client.messages.create(
            model=self._model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(block, "text", "") for block in msg.content)
        lines = [ln.strip("-•* \t") for ln in text.splitlines() if ln.strip()]
        return [ln for ln in lines if ln]
