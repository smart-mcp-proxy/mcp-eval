"""Freeze the tool corpus from a running mcpproxy (FR-012, CN-002).

Source of truth: ``GET /api/v1/tools`` (global tools, spec 050), which returns
every tool's ``name``, ``server_name``, ``description`` and ``schema`` under the
``{"success": true, "data": {"tools": [...]}}`` envelope (see
internal/httpapi/server.go ``handleGetGlobalTools``).
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from .models import Corpus, CorpusTool


class ToolsSource(Protocol):
    def list_tools(self) -> list[dict[str, Any]]: ...


class ToolsClient:
    """Live ``ToolsSource`` backed by httpx."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key},
            transport=transport,
            timeout=timeout,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/v1/tools")
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        return data.get("tools") or []

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ToolsClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def snapshot_corpus(source: ToolsSource, *, version: str = "corpus_v1", note: str = "") -> Corpus:
    """Build a :class:`Corpus` from the live ``/api/v1/tools`` enumeration."""
    tools: list[CorpusTool] = []
    for raw in source.list_tools():
        server = raw.get("server_name", "")
        name = raw.get("name", "")
        if not server or not name:
            continue
        tools.append(
            CorpusTool(
                tool_id=f"{server}:{name}",
                server=server,
                tool=name,
                description=raw.get("description", "") or "",
                schema=raw.get("schema"),
            )
        )
    tools.sort(key=lambda t: t.tool_id)  # deterministic, reproducible snapshots
    return Corpus(
        version=version,
        generated_from={"source": "GET /api/v1/tools", "note": note},
        tools=tools,
    )
