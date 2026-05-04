"""
Pytest configuration: ensure OPENAI_API_KEY is present so importing AINewsAgent never exits at import time.
"""

import pytest


@pytest.fixture(autouse=True)
def dummy_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-not-real")


@pytest.fixture(autouse=True)
def isolate_seen_articles_store(monkeypatch, tmp_path):
    """Avoid writing cross-run state into the real workspace during tests."""
    monkeypatch.setenv("SEEN_ARTICLES_PATH", str(tmp_path / "seen_articles.json"))
