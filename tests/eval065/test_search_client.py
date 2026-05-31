"""SearchClient + snapshot ToolsClient against a mocked httpx transport (R-01/R-02).

No live proxy in unit tests; an httpx.MockTransport emulates the REST contract
(`{success, data:{...}}` envelope from internal/httpapi).
"""

from __future__ import annotations

import json

import httpx

from mcp_eval.datasets.snapshot import ToolsClient, snapshot_corpus
from mcp_eval.retrieval.search_client import SearchClient


def _search_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/v1/index/search"
    assert request.headers.get("X-API-Key") == "uitest"
    q = request.url.params.get("q")
    payload = {
        "success": True,
        "data": {
            "query": q,
            "results": [
                {"tool": {"name": "create_issue", "server_name": "github"}, "score": 9.5},
                {"tool": {"name": "run_container", "server_name": "docker"}, "score": 1.2},
            ],
            "total": 2,
            "took": "1ms",
        },
    }
    return httpx.Response(200, content=json.dumps(payload))


def test_search_client_joins_tool_id():
    transport = httpx.MockTransport(_search_handler)
    client = SearchClient(base_url="http://127.0.0.1:8080", api_key="uitest", transport=transport)
    results = client.search("file a bug", limit=5)
    assert [r.tool_id for r in results] == ["github:create_issue", "docker:run_container"]
    assert results[0].score == 9.5


def _tools_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/v1/tools"
    payload = {
        "success": True,
        "data": {
            "tools": [
                {
                    "name": "create_issue",
                    "server_name": "github",
                    "description": "Open an issue.",
                    "schema": {"type": "object"},
                },
                {
                    "name": "run_container",
                    "server_name": "docker",
                    "description": "Run a container.",
                    "schema": {"type": "object"},
                },
            ],
            "stats": {"total": 2},
        },
    }
    return httpx.Response(200, content=json.dumps(payload))


def test_snapshot_builds_corpus_from_tools_endpoint():
    transport = httpx.MockTransport(_tools_handler)
    client = ToolsClient(base_url="http://127.0.0.1:8080", api_key="uitest", transport=transport)
    corpus = snapshot_corpus(client, note="unit test")
    ids = {t.tool_id for t in corpus.tools}
    assert ids == {"github:create_issue", "docker:run_container"}
    gh = next(t for t in corpus.tools if t.tool_id == "github:create_issue")
    assert gh.description == "Open an issue."
    assert gh.json_schema == {"type": "object"}
    assert corpus.generated_from["source"] == "GET /api/v1/tools"
