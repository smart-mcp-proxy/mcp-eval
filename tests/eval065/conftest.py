"""Shared fixtures for the Spec 065 D1 retrieval-eval tests."""

from __future__ import annotations

import pytest

from mcp_eval.datasets.models import Corpus, CorpusTool, GoldenSet, Label, Query


@pytest.fixture
def corpus() -> Corpus:
    """A tiny three-tool corpus across two servers."""
    return Corpus(
        version="corpus_test",
        generated_from={"source": "fixture", "note": "unit test"},
        tools=[
            CorpusTool(
                tool_id="github:create_issue",
                server="github",
                tool="create_issue",
                description="Open a new issue on a GitHub repository.",
                schema={"type": "object"},
            ),
            CorpusTool(
                tool_id="gitlab:create_issue",
                server="gitlab",
                tool="create_issue",
                description="Open a new issue on a GitLab project.",
                schema={"type": "object"},
            ),
            CorpusTool(
                tool_id="docker:run_container",
                server="docker",
                tool="run_container",
                description="Start a container from an image.",
                schema={"type": "object"},
            ),
        ],
    )


@pytest.fixture
def golden(corpus: Corpus) -> GoldenSet:
    """A golden set whose labels all reference tools in `corpus`."""
    return GoldenSet(
        corpus_version=corpus.version,
        queries=[
            Query(
                id="q0001",
                query="file a bug report against a code repository",
                labels=[
                    Label(tool_id="github:create_issue", relevance=2),
                    Label(tool_id="gitlab:create_issue", relevance=1),
                ],
            ),
            Query(
                id="q0002",
                query="spin up an isolated runtime from a prebuilt image",
                labels=[Label(tool_id="docker:run_container", relevance=2)],
            ),
        ],
    )
