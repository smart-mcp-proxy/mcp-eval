"""HTTP client driving the mcpproxy retrieval endpoint (R-01/R-02/R-D).

``SearchClient`` calls ``GET /api/v1/index/search?q=&limit=`` with an
``X-API-Key`` header and returns ranked ``ScoredTool``s joined on
``tool_id = "<server>:<tool>"``. The mcpproxy REST envelope is
``{"success": true, "data": {"results": [{"tool": {...}, "score": ...}]}}``
(see internal/httpapi/server.go ``handleSearchTools``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class ScoredTool:
    tool_id: str
    score: float


class SearchBackend(Protocol):
    """The minimal surface the scorer depends on (injectable for tests)."""

    def search(self, query: str, limit: int) -> list[ScoredTool]: ...


def _join_tool_id(tool: dict[str, Any]) -> str:
    return f"{tool.get('server_name', '')}:{tool.get('name', '')}"


class SearchClient:
    """Live ``SearchBackend`` backed by httpx."""

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

    def search(self, query: str, limit: int) -> list[ScoredTool]:
        resp = self._client.get(
            "/api/v1/index/search", params={"q": query, "limit": limit}
        )
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        results = data.get("results") or []
        out: list[ScoredTool] = []
        for item in results:
            tool = item.get("tool") or {}
            out.append(
                ScoredTool(tool_id=_join_tool_id(tool), score=float(item.get("score", 0.0)))
            )
        return out

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SearchClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
