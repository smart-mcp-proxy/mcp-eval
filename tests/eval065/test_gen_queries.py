"""gen-queries R-C guard: a generated query must never name the tool (R-C)."""

from __future__ import annotations

from mcp_eval.datasets.gen_queries import generate_queries, names_tool
from mcp_eval.datasets.models import Corpus, CorpusTool


class ScriptedGenerator:
    """Returns a fixed list of candidates per tool, including a banned one."""

    def __init__(self, candidates: list[str]):
        self._candidates = candidates

    def generate(self, tool: CorpusTool, n: int) -> list[str]:
        return list(self._candidates)


def test_names_tool_detects_verbatim_name():
    tool = CorpusTool(tool_id="github:create_issue", server="github", tool="create_issue")
    assert names_tool("please create_issue for me", tool) is True
    assert names_tool("call github:create_issue now", tool) is True
    assert names_tool("file a bug on the repo", tool) is False


def test_gen_queries_rejects_tool_naming_candidates():
    corpus = Corpus(
        version="c",
        generated_from={"source": "fixture"},
        tools=[CorpusTool(tool_id="github:create_issue", server="github", tool="create_issue")],
    )
    gen = ScriptedGenerator(
        [
            "use create_issue to open a ticket",  # BANNED — names the tool
            "open a ticket on the repository",  # ok
            "report a defect in the project",  # ok
        ]
    )
    golden = generate_queries(corpus, gen, per_tool=2)
    assert len(golden.queries) == 2
    for q in golden.queries:
        assert "create_issue" not in q.query.lower()
        assert q.labels[0].tool_id == "github:create_issue"
