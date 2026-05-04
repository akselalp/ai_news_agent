"""AINewsAgent unit tests with OpenAI client mocked."""

from unittest.mock import MagicMock

import pytest

import ai_news_agent as mod


@pytest.fixture
def patch_openai_client(monkeypatch):
    mock_cls = MagicMock()
    monkeypatch.setattr(mod, "OpenAI", mock_cls)
    return mock_cls


def test_deepmind_and_gemini_use_rss(patch_openai_client):
    agent = mod.AINewsAgent()
    assert agent.sources["deepmind"]["parser"] == "rss"
    assert "rss.xml" in agent.sources["deepmind"]["url"]
    assert agent.sources["gemini"]["parser"] == "rss"
    assert "blog.google" in agent.sources["gemini"]["url"]


def test_generate_markdown_content(patch_openai_client):
    agent = mod.AINewsAgent()
    agent.top_articles = [
        mod.Article(
            title="Hello",
            url="https://ex.com",
            source="src",
            summary="Sum.",
        )
    ]
    md = agent._generate_markdown_content("2026-05-04")
    assert "Hello" in md and "Sum." in md and "2026-05-04" in md
