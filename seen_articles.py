"""
Cross-run article memory: avoid surfacing the same RSS/API items day after day.

Persists normalized URLs, title fingerprints, URL slug keys, and core title keys
with configurable cooldowns. Recording runs only after a successful digest output;
by default only ranked digest placements are recorded (`SEEN_RECORD_SCOPE=digest`
in `ai_news_agent.py`).
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

_TRACKING_QUERY_KEYS = frozenset(
    k.lower()
    for k in (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
    )
)

# Strip trailing " | TechCrunch" / " — NVIDIA Blog" style noise so syndicated hed lines match.
_OUTLET_SUFFIX_RE = re.compile(
    r"\s*(?:\||\u2013|\u2014)\s*("
    r"tech\s*crunch|the\s*verge|wired|nvidia\s*blog|nvidia|openai|anthropic|deepmind|"
    r"google\s*ai|google\s*developers|blog\.google|hugging\s*face|huggingface|"
    r"artificial\s*intelligence\s*news|ai\s*news|venturebeat|zdnet|ars\s*technica|"
    r"bloomberg|reuters|mit\s*technology\s*review|forbes|cnbc|wsj|the\s*information|"
    r"medium"
    r")\s*$",
    re.I,
)
_TRAILING_DASH_OUTLET = re.compile(
    r"\s+-\s*(tech\s*crunch|the\s*verge|wired|nvidia|openai|venturebeat)\s*$",
    re.I,
)


def normalize_url(url: str) -> str:
    """Stable URL key: scheme/host lowercase, strip fragment, drop tracking query params, strip trailing slash."""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlparse(raw)
        scheme = (parts.scheme or "http").lower()
        netloc = (parts.netloc or "").lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path or ""
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        q_pairs = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=False)
            if k.lower() not in _TRACKING_QUERY_KEYS
        ]
        q_pairs.sort()
        query = urlencode(q_pairs)
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return raw.strip().lower()


def title_fingerprint(title: str) -> str:
    """Normalize headline for syndication dedupe (same story, different URLs)."""
    t = (title or "").strip()
    if not t:
        return ""
    t = re.sub(r"^\d+\.\s+", "", t)
    t = t.lower()
    for _ in range(5):
        t2 = _OUTLET_SUFFIX_RE.sub("", t).strip()
        t2 = _TRAILING_DASH_OUTLET.sub("", t2).strip()
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[\W_]+|[\W_]+$", "", t)
    return t[:280]


def core_title_key(title: str) -> str:
    """
    Alphanumeric prefix of the normalized title — catches same story with minor wording drift
    across outlets when full title_fingerprint differs.
    """
    fp = title_fingerprint(title)
    if not fp:
        return ""
    alnum = re.sub(r"[^a-z0-9]", "", fp)
    if len(alnum) < 28:
        return ""
    return alnum[:120]


def url_slug_key(url: str) -> str:
    """
    Last URL path segment (letters/digits only) — helps when the story slug is identical
    across mirrors (not universal; gated by minimum length).
    """
    nu = normalize_url(url)
    if not nu:
        return ""
    path = urlparse(nu).path.strip("/")
    if not path:
        return ""
    seg = path.split("/")[-1]
    seg = unquote(seg)
    seg = re.sub(r"\.(html?|php|xml|md)$", "", seg, flags=re.I)
    slug = re.sub(r"[^a-z0-9]+", "", seg.lower())
    if len(slug) < 18:
        return ""
    return slug[:160]


def _parse_iso_ts(s: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r — using default %s", name, raw, default)
        return default


def _env_int_optional(name: str) -> Optional[int]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r — ignoring", name, raw)
        return None


def cross_run_dedupe_enabled() -> bool:
    return (os.getenv("CROSS_RUN_DEDUPE") or "true").strip().lower() not in ("0", "false", "no", "off")


@dataclass
class SeenStats:
    skipped_urls: int = 0
    skipped_titles: int = 0
    skipped_slugs: int = 0
    skipped_cores: int = 0
    kept: int = 0


class SeenArticlesStore:
    """JSON-backed store for URLs, titles, slugs, and core-title keys with TTL cooldowns."""

    def __init__(
        self,
        path: Path,
        *,
        url_cooldown_days: int,
        title_cooldown_days: int,
        slug_cooldown_days: int,
        core_cooldown_days: int,
        retention_days: int,
    ) -> None:
        self.path = path.resolve()
        self.url_cooldown = timedelta(days=max(1, url_cooldown_days))
        self.title_cooldown = timedelta(days=max(1, title_cooldown_days))
        self.slug_cooldown = timedelta(days=max(1, slug_cooldown_days))
        self.core_cooldown = timedelta(days=max(1, core_cooldown_days))
        self.retention = timedelta(days=max(30, retention_days))
        self._urls: Dict[str, str] = {}
        self._titles: Dict[str, str] = {}
        self._slugs: Dict[str, str] = {}
        self._cores: Dict[str, str] = {}
        self._load()

    @classmethod
    def maybe_load_from_env(cls) -> Optional["SeenArticlesStore"]:
        if not cross_run_dedupe_enabled():
            logger.info("Cross-run dedupe disabled (CROSS_RUN_DEDUPE=false)")
            return None
        raw_path = (os.getenv("SEEN_ARTICLES_PATH") or "data/seen_articles.json").strip()
        path = Path(raw_path)
        if not path.is_absolute():
            root = Path(__file__).resolve().parent
            path = (root / path).resolve()
        url_cd = _env_int("URL_COOLDOWN_DAYS", 120)
        title_cd = _env_int("TITLE_COOLDOWN_DAYS", 90)
        slug_cd = _env_int_optional("SLUG_COOLDOWN_DAYS") or url_cd
        core_cd = _env_int_optional("CORE_TITLE_COOLDOWN_DAYS") or title_cd
        retention = _env_int("SEEN_STORE_RETENTION_DAYS", 548)
        store = cls(
            path,
            url_cooldown_days=url_cd,
            title_cooldown_days=title_cd,
            slug_cooldown_days=slug_cd,
            core_cooldown_days=core_cd,
            retention_days=retention,
        )
        logger.info(
            "Cross-run dedupe on: path=%s url=%sd title=%sd slug=%sd core=%sd retention=%sd",
            store.path,
            url_cd,
            title_cd,
            slug_cd,
            core_cd,
            retention,
        )
        return store

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data.get("urls"), dict):
                self._urls = {str(k): str(v) for k, v in data["urls"].items()}
            if isinstance(data.get("titles"), dict):
                self._titles = {str(k): str(v) for k, v in data["titles"].items()}
            if isinstance(data.get("slugs"), dict):
                self._slugs = {str(k): str(v) for k, v in data["slugs"].items()}
            if isinstance(data.get("cores"), dict):
                self._cores = {str(k): str(v) for k, v in data["cores"].items()}
        except Exception as e:
            logger.warning("Could not load seen-articles store (%s): %s — starting fresh", self.path, e)
            self._urls = {}
            self._titles = {}
            self._slugs = {}
            self._cores = {}

    def _prune(self, now: datetime) -> None:
        cutoff = now - self.retention

        def _keep(mapping: Dict[str, str]) -> Dict[str, str]:
            out: Dict[str, str] = {}
            for k, ts in mapping.items():
                dt = _parse_iso_ts(ts)
                if dt and dt >= cutoff:
                    out[k] = ts
            return out

        nu, nt = _keep(self._urls), _keep(self._titles)
        ns, nc = _keep(self._slugs), _keep(self._cores)
        before = len(self._urls) + len(self._titles) + len(self._slugs) + len(self._cores)
        after = len(nu) + len(nt) + len(ns) + len(nc)
        if before > after:
            logger.debug("Pruned seen store entries: %s → %s", before, after)
        self._urls, self._titles, self._slugs, self._cores = nu, nt, ns, nc

    def _atomic_write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=".seen_articles_",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def save(self) -> None:
        now = datetime.now(timezone.utc)
        self._prune(now)
        payload = {
            "version": 2,
            "updated_at": now.isoformat(),
            "urls": dict(sorted(self._urls.items())),
            "titles": dict(sorted(self._titles.items())),
            "slugs": dict(sorted(self._slugs.items())),
            "cores": dict(sorted(self._cores.items())),
        }
        self._atomic_write(payload)

    def _seen_recently(self, mapping: Dict[str, str], key: str, cooldown: timedelta, now: datetime) -> bool:
        ts = mapping.get(key)
        if not ts:
            return False
        dt = _parse_iso_ts(ts)
        if not dt:
            return False
        return now - dt < cooldown

    def filter_articles(self, articles: List[Any], *, now: Optional[datetime] = None) -> Tuple[List[Any], SeenStats]:
        """Drop articles whose URL, slug, title, or core key was recently processed."""
        stats = SeenStats()
        now = now or datetime.now(timezone.utc)
        kept: List[Any] = []
        for a in articles:
            url = normalize_url(getattr(a, "url", "") or "")
            title_fp = title_fingerprint(getattr(a, "title", "") or "")
            slug_k = url_slug_key(getattr(a, "url", "") or "")
            core_k = core_title_key(getattr(a, "title", "") or "")

            if url and self._seen_recently(self._urls, url, self.url_cooldown, now):
                stats.skipped_urls += 1
                continue
            if slug_k and self._seen_recently(self._slugs, slug_k, self.slug_cooldown, now):
                stats.skipped_slugs += 1
                continue
            if title_fp and self._seen_recently(self._titles, title_fp, self.title_cooldown, now):
                stats.skipped_titles += 1
                continue
            if core_k and self._seen_recently(self._cores, core_k, self.core_cooldown, now):
                stats.skipped_cores += 1
                continue
            kept.append(a)
        stats.kept = len(kept)
        if stats.skipped_urls or stats.skipped_titles or stats.skipped_slugs or stats.skipped_cores:
            logger.info(
                "Cross-run dedupe: skip url=%s slug=%s title=%s core=%s → kept=%s",
                stats.skipped_urls,
                stats.skipped_slugs,
                stats.skipped_titles,
                stats.skipped_cores,
                stats.kept,
            )
        return kept, stats

    def record_processed_batch(self, articles: List[Any], *, now: Optional[datetime] = None) -> None:
        """Mark URLs/titles/slugs/cores as processed after a successful digest."""
        now = now or datetime.now(timezone.utc)
        iso = now.isoformat()
        for a in articles:
            url = normalize_url(getattr(a, "url", "") or "")
            title_fp = title_fingerprint(getattr(a, "title", "") or "")
            slug_k = url_slug_key(getattr(a, "url", "") or "")
            core_k = core_title_key(getattr(a, "title", "") or "")
            if url:
                self._urls[url] = iso
            if title_fp:
                self._titles[title_fp] = iso
            if slug_k:
                self._slugs[slug_k] = iso
            if core_k:
                self._cores[core_k] = iso
        try:
            self.save()
            logger.info("Recorded %s articles → seen store %s", len(articles), self.path)
        except Exception as e:
            logger.error("Failed to persist seen-articles store: %s", e)
