"""Tests for cross-run seen-articles memory."""

from datetime import datetime, timedelta, timezone

from seen_articles import (
    SeenArticlesStore,
    core_title_key,
    normalize_url,
    title_fingerprint,
    url_slug_key,
)


def test_normalize_url_strips_www():
    assert normalize_url("https://WWW.Example.COM/foo") == "https://example.com/foo"


def test_normalize_url_strips_utm():
    a = "https://Example.COM/foo/bar/?utm_source=x&id=1"
    b = "https://example.com/foo/bar?id=1"
    assert normalize_url(a) == normalize_url(b)


def test_title_fingerprint_collapses_whitespace():
    assert title_fingerprint("Hello   World") == title_fingerprint("hello world")


def test_syndicated_headlines_normalize_identically():
    a = "NVIDIA Launches Nemotron 3 | TechCrunch"
    b = "NVIDIA Launches Nemotron 3 — NVIDIA Blog"
    assert title_fingerprint(a) == title_fingerprint(b)


def test_core_title_collapses_minor_word_differences():
    t1 = "Converge Bio raises $25M, backed by Bessemer"
    t2 = "Converge Bio Raises $25M, Backed By Bessemer"
    assert core_title_key(t1) == core_title_key(t2)


def test_slug_key_matches_last_segment_across_hosts():
    u1 = "https://a.com/2026/01/nemotron-3-nano-launch"
    u2 = "https://b.com/news/nemotron-3-nano-launch"
    assert url_slug_key(u1) == url_slug_key(u2)


def test_seen_store_respects_url_cooldown(tmp_path):
    p = tmp_path / "s.json"
    store = SeenArticlesStore(
        p,
        url_cooldown_days=7,
        title_cooldown_days=7,
        slug_cooldown_days=7,
        core_cooldown_days=7,
        retention_days=60,
    )
    now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)

    class A:
        def __init__(self, title, url):
            self.title = title
            self.url = url

    batch = [A("Paper on AI", "https://arxiv.org/abs/1234")]
    kept, st = store.filter_articles(batch, now=now)
    assert len(kept) == 1 and st.kept == 1

    store.record_processed_batch(batch, now=now)
    assert p.exists()

    soon = now + timedelta(days=3)
    kept2, st2 = store.filter_articles(batch, now=soon)
    assert len(kept2) == 0 and st2.skipped_urls >= 1

    later = now + timedelta(days=10)
    kept3, st3 = store.filter_articles(batch, now=later)
    assert len(kept3) == 1


def test_slug_skip_when_urls_differ_but_slug_matches(tmp_path):
    p = tmp_path / "slug.json"
    store = SeenArticlesStore(
        p,
        url_cooldown_days=30,
        title_cooldown_days=30,
        slug_cooldown_days=30,
        core_cooldown_days=30,
        retention_days=90,
    )
    now = datetime.now(timezone.utc)

    class A:
        def __init__(self, title, url):
            self.title = title
            self.url = url

    a1 = A("x", "https://a.com/2026/01/nemotron-3-nano-launch-extra")
    a2 = A("y", "https://b.com/p/nemotron-3-nano-launch-extra")
    assert url_slug_key(a1.url) == url_slug_key(a2.url)
    store.record_processed_batch([a1], now=now)
    kept, st = store.filter_articles([a2], now=now + timedelta(minutes=5))
    assert len(kept) == 0
    assert st.skipped_slugs >= 1


def test_title_dup_blocked_when_url_differs(tmp_path):
    p = tmp_path / "s2.json"
    store = SeenArticlesStore(
        p,
        url_cooldown_days=30,
        title_cooldown_days=30,
        slug_cooldown_days=30,
        core_cooldown_days=30,
        retention_days=90,
    )
    now = datetime.now(timezone.utc)

    class A:
        def __init__(self, url):
            self.title = "Same Headline Everywhere"
            self.url = url

    a1 = A("https://a.com/x")
    a2 = A("https://b.com/y")
    store.record_processed_batch([a1], now=now)
    kept, st = store.filter_articles([a2], now=now + timedelta(hours=2))
    assert len(kept) == 0
    assert st.skipped_titles >= 1
