"""Unit tests for agent_support helpers (no network)."""

from datetime import datetime, timezone

from agent_support import (
    clean_scraped_news_title,
    completion_output_kw,
    filter_articles_by_date,
    parse_published_datetime,
    ranked_indices_from_llm,
)
from ai_news_agent import Article


def test_completion_output_kw_prefers_max_completion_tokens_for_gpt5_family():
    assert completion_output_kw("gpt-5-nano", 50) == {"max_completion_tokens": 50}


def test_completion_output_kw_uses_max_tokens_for_mini_models():
    assert completion_output_kw("gpt-4o-mini", 50) == {"max_tokens": 50}


def test_ranked_indices_from_llm_json():
    raw = '{"ranked_article_numbers":[3, 1, 2]}'
    r = ranked_indices_from_llm(raw, effective_top_n=3, total_articles=5)
    assert r.method.startswith("json")
    assert r.indices_0based == [2, 0, 1]


def test_ranked_indices_from_llm_regex_fallback():
    raw = "Here: 2, 4, 1"
    r = ranked_indices_from_llm(raw, effective_top_n=3, total_articles=10)
    assert r.method == "regex"
    assert r.indices_0based == [1, 3, 0]


def test_ranked_indices_from_llm_incomplete_triggers_fallback_marker():
    raw = '{"ranked_article_numbers":[1]}'
    r = ranked_indices_from_llm(raw, effective_top_n=3, total_articles=10)
    assert r.method == "fallback_first_n"


def test_filter_articles_by_date_utc_day():
    articles = [
        Article(
            title="a",
            url="https://a",
            source="s",
            published_date="Mon, 03 May 2026 12:00:00 GMT",
        ),
        Article(
            title="b",
            url="https://b",
            source="s",
            published_date="Sun, 02 May 2026 12:00:00 GMT",
        ),
        Article(title="c", url="https://c", source="s", published_date=""),
    ]
    kept, stats = filter_articles_by_date(articles, "2026-05-03", keep_if_unknown=True)
    titles = {x.title for x in kept}
    assert titles == {"a", "c"}
    assert stats["dropped_wrong_day"] >= 1


def test_parse_published_datetime_iso_z():
    dt = parse_published_datetime("2026-05-03T15:00:00Z")
    assert dt == datetime(2026, 5, 3, 15, 0, tzinfo=timezone.utc)


def test_clean_scraped_news_title_anthropic_claude_design_blob():
    raw = (
        "ProductApr 17, 2026Introducing Claude Design by Anthropic LabsToday, "
        "we're launching Claude Design, a new product"
    )
    assert clean_scraped_news_title(raw) == "Introducing Claude Design by Anthropic Labs"


def test_clean_scraped_news_title_anthropic_81k_study_blob():
    raw = "Mar 18, 2026What 81,000 people want from AIWe invited Claude.ai users to share"
    assert clean_scraped_news_title(raw) == "What 81,000 people want from AI"
