"""Pipeline edge cases: empty corpus, dry-run, no wasted LLM calls."""

from unittest.mock import MagicMock

import ai_news_agent as mod


def test_pipeline_skips_llm_when_no_articles(monkeypatch):
    mock_cls = MagicMock()
    monkeypatch.setattr(mod, "OpenAI", mock_cls)
    agent = mod.AINewsAgent()

    def fake_get(*a, **k):
        agent.articles = []
        return []

    agent.get_articles = fake_get  # type: ignore[method-assign]

    out = agent.run_daily_pipeline("2026-05-04", "markdown")
    assert out == ""
    mock_cls.return_value.chat.completions.create.assert_not_called()


def test_dry_run_skips_llm(monkeypatch):
    mock_cls = MagicMock()
    monkeypatch.setattr(mod, "OpenAI", mock_cls)
    agent = mod.AINewsAgent()

    def fake_get(*a, **k):
        agent.articles = [
            mod.Article(title="T", url="https://example.com/a", source="test"),
        ]
        return agent.articles

    agent.get_articles = fake_get  # type: ignore[method-assign]

    out = agent.run_daily_pipeline("2026-05-04", "markdown", dry_run=True)
    assert out == ""
    mock_cls.return_value.chat.completions.create.assert_not_called()
