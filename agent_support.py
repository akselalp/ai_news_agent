"""
Shared helpers for AI News Agent: model defaults, completion parameters,
ranking response parsing, and article date handling.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Documented defaults when SUMMARY_MODEL / RANK_MODEL are unset (see README).
DEFAULT_SUMMARY_MODEL = "gpt-4o-mini"
DEFAULT_RANK_MODEL = "gpt-4o-mini"


def summary_model_from_env() -> str:
    import os

    v = (os.getenv("SUMMARY_MODEL") or "").strip()
    return v or DEFAULT_SUMMARY_MODEL


def rank_model_from_env() -> str:
    import os

    v = (os.getenv("RANK_MODEL") or "").strip()
    return v or DEFAULT_RANK_MODEL


def completion_output_kw(model: str, limit: int) -> dict:
    """Use max_completion_tokens for newer model families; max_tokens otherwise."""
    m = (model or "").lower()
    if m.startswith(("gpt-5", "o1", "o3", "o4")):
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def parse_published_datetime(published: Optional[str]) -> Optional[datetime]:
    """Best-effort parse of feed/article date strings to timezone-aware UTC."""
    if not published or not str(published).strip():
        return None
    s = str(published).strip()
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def target_date_utc_bounds(target: str) -> Tuple[datetime, datetime]:
    """Inclusive UTC day bounds for YYYY-MM-DD."""
    d = date.fromisoformat(target)
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def article_matches_target_date(article: Any, target: str) -> bool:
    """True if article published date falls on target calendar day (UTC)."""
    dt = parse_published_datetime(getattr(article, "published_date", None))
    if dt is None:
        return False
    start, end = target_date_utc_bounds(target)
    return start <= dt <= end


def filter_articles_by_date(
    articles: List[Any],
    target: Optional[str],
    *,
    keep_if_unknown: bool = True,
) -> Tuple[List["Article"], dict]:
    """
    Keep articles whose published_date falls on target day (UTC).
    If keep_if_unknown, articles without a parseable date are kept and counted.
    Returns (filtered_list, stats dict).
    """
    if not target:
        return articles, {"mode": "none", "input": len(articles), "output": len(articles)}

    kept: List[Any] = []
    unknown = 0
    dropped = 0
    for a in articles:
        dt = parse_published_datetime(getattr(a, "published_date", None))
        if dt is None:
            unknown += 1
            if keep_if_unknown:
                kept.append(a)
            else:
                dropped += 1
            continue
        if article_matches_target_date(a, target):
            kept.append(a)
        else:
            dropped += 1

    stats = {
        "mode": "utc_calendar_day",
        "target": target,
        "input": len(articles),
        "output": len(kept),
        "unknown_pub_date": unknown,
        "dropped_wrong_day": dropped,
    }
    logger.info(
        "Date filter: target=%s kept=%s/%s (unknown_dates_kept=%s wrong_day_dropped=%s)",
        target,
        len(kept),
        len(articles),
        unknown if keep_if_unknown else 0,
        dropped,
    )
    return kept, stats


@dataclass
class RankingParseResult:
    indices_0based: List[int]
    method: str  # json_object | json_relaxed | regex | fallback_first_n


_JSON_NUMBERS_RE = re.compile(r"\d+")


def _strip_json_fence(raw: str) -> str:
    t = raw.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _indices_from_json_obj(obj: dict, effective_top_n: int, total: int) -> Optional[List[int]]:
    nums = obj.get("ranked_article_numbers")
    if nums is None:
        nums = obj.get("indices")
    if nums is None:
        nums = obj.get("article_numbers")
    if not isinstance(nums, list):
        return None
    out: List[int] = []
    seen = set()
    for x in nums:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        idx = n - 1
        if n <= 0 or idx < 0 or idx >= total or idx in seen:
            continue
        seen.add(idx)
        out.append(idx)
        if len(out) == effective_top_n:
            break
    if len(out) < effective_top_n:
        return None
    return out


def ranked_indices_from_llm(
    raw_text: str,
    *,
    effective_top_n: int,
    total_articles: int,
) -> RankingParseResult:
    """
    Parse model output into distinct 0-based indices in rank order.
    Tries strict JSON, relaxed JSON extraction, digit extraction, then signals fallback.
    """
    text = (raw_text or "").strip()
    if not text:
        return RankingParseResult([], "fallback_first_n")

    # 1) JSON object
    try:
        obj = json.loads(_strip_json_fence(text))
        if isinstance(obj, dict):
            got = _indices_from_json_obj(obj, effective_top_n, total_articles)
            if got is not None:
                return RankingParseResult(got, "json_object")
    except json.JSONDecodeError:
        pass

    # 2) First {...} slice
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                got = _indices_from_json_obj(obj, effective_top_n, total_articles)
                if got is not None:
                    return RankingParseResult(got, "json_relaxed")
        except json.JSONDecodeError:
            pass

    # 3) Regex digits (legacy)
    numbers = [int(n) for n in _JSON_NUMBERS_RE.findall(text)]
    seen = set()
    top_indices: List[int] = []
    for n in numbers:
        idx = n - 1
        if n <= 0 or idx < 0 or idx >= total_articles or idx in seen:
            continue
        seen.add(idx)
        top_indices.append(idx)
        if len(top_indices) == effective_top_n:
            return RankingParseResult(top_indices, "regex")

    return RankingParseResult([], "fallback_first_n")


def summarize_max_articles_from_env() -> Optional[int]:
    import os

    raw = (os.getenv("SUMMARIZE_MAX_ARTICLES") or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        logger.warning("Invalid SUMMARIZE_MAX_ARTICLES=%r — ignoring", raw)
        return None


def top_n_from_env(default: int = 10) -> int:
    import os

    raw = (os.getenv("TOP_ARTICLES") or "").strip()
    if not raw:
        return default
    try:
        n = int(raw)
        return n if n > 0 else default
    except ValueError:
        return default


_MONTH_NAMES_RE = (
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
)


def clean_scraped_news_title(title: str) -> str:
    """
    Fix titles where HTML card scrapers concatenated adjacent nodes without spaces:
    glued calendar dates, teaser paragraphs, and labels like \"Product\" before the month.
    Intended for Anthropic-style marketing listing pages; safe to reuse for similar layouts.
    """
    t = (title or "").strip()
    if not t:
        return t

    # Word boundary glued to month (ProductApr → Product Apr)
    t = re.sub(rf"([a-zA-Z])({_MONTH_NAMES_RE})\b", r"\1 \2", t, flags=re.I)
    # Four-digit year glued to following word (2026Introducing → 2026 Introducing)
    t = re.sub(r"(20\d{2})([A-Za-z])", r"\1 \2", t)
    # Word glued to sentence starters inside the same blob
    t = re.sub(r"([a-z])(Today\b)", r"\1 \2", t, flags=re.I)
    t = re.sub(r"([a-z])(We\b)", r"\1 \2", t)
    t = re.sub(r"\b(AI)(We\b)", r"\1 \2", t)

    # Strip leading \"Product\" + publication date when present
    t = re.sub(
        rf"^(?:Product\s+)?(?:{_MONTH_NAMES_RE})\s+\d{{1,2}},\s*20\d{{2}}\s*",
        "",
        t,
        flags=re.I,
    )

    # Drop teaser text usually glued after the headline
    for sep in (
        " Today,",
        " today,",
        " We invited",
        " we invited",
        " Here's what we found",
        " here's what we found",
        " Here’s what we found",
    ):
        idx = t.find(sep)
        if idx != -1:
            t = t[:idx].strip()
            break

    t = re.sub(r"\s+", " ", t).strip()
    return t.strip(" ,;:–-")


def log_openai_usage(logger_: logging.Logger, response, operation: str) -> None:
    """Log usage from chat.completion response when present (no secrets)."""
    try:
        u = getattr(response, "usage", None)
        if u is None:
            return
        pt = getattr(u, "prompt_tokens", None)
        ct = getattr(u, "completion_tokens", None)
        tt = getattr(u, "total_tokens", None)
        if pt is not None or ct is not None or tt is not None:
            logger_.info(
                "OpenAI usage [%s]: prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                operation,
                pt,
                ct,
                tt,
            )
    except Exception:
        pass
