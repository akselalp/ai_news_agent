#!/usr/bin/env python3 
# Use the line above if using system's default Python.
# But if you're using a virtual environment, replace line 1 with:
# #!/usr/usr_name/anaconda3/envs/venv_name/bin/python3
"""
AI News Agent — daily AI news digest for practitioners.

Collects from RSS/API/scrape sources, dedupes within-run and across runs (persistent memory),
summarizes with a configurable OpenAI model, ranks via structured JSON, then outputs
Markdown / Notion / email / Slack.

Author: Aksel A.
Date: May-2026
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import feedparser
from datetime import datetime  # , timedelta
from typing import List, Dict, Optional  # , Tuple
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

# Third-party imports
from openai import OpenAI
from openai import BadRequestError
from dotenv import load_dotenv
import schedule
import time

from agent_support import (
    DEFAULT_RANK_MODEL,
    DEFAULT_SUMMARY_MODEL,
    clean_scraped_news_title,
    completion_output_kw,
    filter_articles_by_date,
    log_openai_usage,
    parse_published_datetime,
    rank_model_from_env,
    ranked_indices_from_llm,
    summarize_max_articles_from_env,
    summary_model_from_env,
    top_n_from_env,
)
from seen_articles import (
    SeenArticlesStore,
    core_title_key,
    normalize_url,
    title_fingerprint,
    url_slug_key,
)

# Load environment variables
load_dotenv()


def _logging_env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _fetch_parallel_enabled() -> bool:
    """Parallel HTTP fetch across sources (default on; disable with FETCH_PARALLEL=false)."""
    raw = (os.getenv("FETCH_PARALLEL") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


_LOG_PATH = os.getenv("LOG_FILE_PATH", "ai_news_agent.log").strip() or "ai_news_agent.log"
_handlers: list = [logging.StreamHandler()]
if os.getenv("LOG_DISABLE_ROTATE", "").strip().lower() in ("1", "true", "yes", "on"):
    _handlers.insert(0, logging.FileHandler(_LOG_PATH))
else:
    _handlers.insert(
        0,
        RotatingFileHandler(
            _LOG_PATH,
            maxBytes=max(1_024_000, _logging_env_int("LOG_FILE_MAX_BYTES", 10 * 1024 * 1024)),
            backupCount=max(1, _logging_env_int("LOG_FILE_BACKUP_COUNT", 5)),
        ),
    )

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_TIMEOUT = (10, 30)  # (connect timeout, read timeout) 10 seconds for connect, 30 seconds for read


@dataclass
class Article:
    """Data class to represent an article."""
    title: str
    url: str
    source: str
    published_date: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None


class AINewsAgent:
    """Main class for AI News Agent functionality."""
    
    def __init__(self):
        """Initialize the AI News Agent."""
        self.articles: List[Article] = []
        self.summarized_articles: List[Article] = []
        self.top_articles: List[Article] = []
        self.last_notion_url: Optional[str] = None
        self.summary_model: str = summary_model_from_env()
        self.rank_model: str = rank_model_from_env()
        self._usage_prompt_tokens = 0
        self._usage_completion_tokens = 0
        self._enrich_fetch_count = 0

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            sys.exit(1)

        organization_id = os.getenv("OPENAI_ORGANIZATION_ID")
        project_id = os.getenv("OPENAI_PROJECT_ID")
        
        # News sources configuration - optimized for quality and cost
        self.sources = {
            'arxiv_ai': {
                'url': 'http://export.arxiv.org/rss/cs.AI',
                'parser': 'arxiv',
                'limit': 3  # Limit to most recent
            },
            'arxiv_ml': {
                'url': 'http://export.arxiv.org/rss/cs.LG',
                'parser': 'arxiv',
                'limit': 3
            },
            'hackernews_ai': {
                'url': 'https://hn.algolia.com/api/v1/search?query=AI%20OR%20artificial%20intelligence%20OR%20machine%20learning&tags=story&hitsPerPage=5',
                'parser': 'hackernews_api',
                'limit': 5
            },
            'techcrunch_ai': {
                'url': 'https://techcrunch.com/tag/artificial-intelligence/feed/',
                'parser': 'rss',
                'limit': 5
            },
            'nvidia_blog': {
                'url': 'https://blogs.nvidia.com/feed/',
                'parser': 'rss',
                'limit': 5,
                'filter_keywords': ['AI', 'artificial intelligence', 'machine learning', 'GPU', 'deep learning']
            },
            # Meta Research - RSS feed not available, commenting out for now
            # 'meta_research': {
            #     'url': 'https://research.facebook.com/blog/feed/',
            #     'parser': 'rss',
            #     'limit': 3,
            #     'filter_keywords': ['AI', 'artificial intelligence', 'machine learning', 'neural', 'deep learning']
            # },
            'huggingface': {
                'url': 'https://huggingface.co/blog/feed.xml',
                'parser': 'rss',
                'limit': 5
            },
            'openai_blog': {
                'url': 'https://openai.com/blog/rss.xml',
                'parser': 'rss',
                'limit': 5
            },
            # Google Research - site structure is complex, commenting out for now
            # 'google_research': {
            #     'url': 'https://research.google/blog/',
            #     'parser': 'web_scrape',
            #     'limit': 3,
            #     'filter_keywords': ['AI', 'artificial intelligence', 'machine learning', 'neural', 'deep learning']
            # },
            'deepmind': {
                'url': 'https://deepmind.google/blog/rss.xml',
                'parser': 'rss',
                'limit': 5
            },
            'gemini': {
                'url': 'https://blog.google/technology/ai/rss/',
                'parser': 'rss',
                'limit': 5
            },
            'anthropic': {
                'url': 'https://www.anthropic.com/news',
                'parser': 'web_scrape',
                'limit': 5
            },
            'mistral_ai': {
                'url': 'https://mistral.ai/news/',
                'parser': 'web_scrape',
                'limit': 5
            },
            # Qwen - blog page is empty, commenting out for now
            # 'qwen': {
            #     'url': 'https://qwen.ai/blog',
            #     'parser': 'web_scrape',
            #     'limit': 3
            # },
            # ASML - site structure is complex, commenting out for now
            # 'asml': {
            #     'url': 'https://www.asml.com/en/news/press-releases',
            #     'parser': 'web_scrape',
            #     'limit': 3,
            #     'filter_keywords': ['AI', 'artificial intelligence', 'machine learning', 'chip', 'semiconductor']
            # },
            'ai_news': {
                'url': 'https://artificialintelligence-news.com/feed/',
                'parser': 'rss',
                'limit': 5
            }
        }

        # Reuse HTTP connections (faster + fewer TLS handshakes)
        self.http = requests.Session()
        self.http.headers.update(DEFAULT_HEADERS)

        # Create ONE OpenAI client and reuse it
        client_kwargs = {}
        if organization_id:
            client_kwargs["organization"] = organization_id
        if project_id:
            client_kwargs["project"] = project_id

        self.client = OpenAI(api_key=api_key, **client_kwargs)

        self.seen_store: Optional[SeenArticlesStore] = SeenArticlesStore.maybe_load_from_env()

        logger.info(
            "Models: SUMMARY_MODEL=%s (default %s), RANK_MODEL=%s (default %s)",
            self.summary_model,
            DEFAULT_SUMMARY_MODEL,
            self.rank_model,
            DEFAULT_RANK_MODEL,
        )

    def _sort_articles_by_recency(self, articles: List[Article]) -> List[Article]:
        """Newest first by parsed published_date; unknown dates sort last."""

        def sort_key(a: Article) -> float:
            dt = parse_published_datetime(a.published_date)
            return dt.timestamp() if dt else float("-inf")

        return sorted(articles, key=sort_key, reverse=True)

    def _digest_output_succeeded(self, output_format: str, output: str) -> bool:
        """Whether downstream delivery succeeded enough to remember this digest (cross-run dedupe)."""
        if not (output or "").strip():
            return False
        if output_format == "notion":
            return bool(self.last_notion_url)
        return True

    def _with_retries(self, fn, max_tries: int = 4):
        """Retry helper for flaky network/429/5xx errors (not for 400-level bad requests)."""
        import random
        from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError

        for attempt in range(max_tries):
            try:
                return fn()

            # Don't retry invalid requests
            except BadRequestError:
                raise

            # Retry these
            except (RateLimitError, APIError, APIConnectionError, APITimeoutError) as e:
                if attempt == max_tries - 1:
                    raise
                sleep_s = (2 ** attempt) + random.random()
                logger.warning(f"Retrying after error: {e} (sleep {sleep_s:.2f}s)")
                time.sleep(sleep_s)

            # For anything else, keep your current behavior (optional)
            except Exception as e:
                if attempt == max_tries - 1:
                    raise
                sleep_s = (2 ** attempt) + random.random()
                logger.warning(f"Retrying after error: {e} (sleep {sleep_s:.2f}s)")
                time.sleep(sleep_s)

    def _accumulate_usage(self, response) -> None:
        """Track token usage from a chat completion response (for run totals)."""
        u = getattr(response, "usage", None)
        if u is None:
            return
        pt = getattr(u, "prompt_tokens", None)
        ct = getattr(u, "completion_tokens", None)
        if isinstance(pt, int):
            self._usage_prompt_tokens += pt
        if isinstance(ct, int):
            self._usage_completion_tokens += ct
    
    def get_articles(
        self,
        date: Optional[str] = None,
        *,
        filter_by_date: bool = False,
    ) -> List[Article]:
        """
        Fetch articles from all configured sources.

        Args:
            date: Optional date string in YYYY-MM-DD format (used for output labeling and optional filtering).
            filter_by_date: When True (see `--filter-by-date` or ARTICLE_DATE_FILTER), keep only articles
                  whose published date falls on `date` in UTC (best-effort). Entries without a parseable
                  publication date are kept by default; set DATE_FILTER_KEEP_UNKNOWN=false to drop them.

        Returns:
            List of Article objects
        """
        logger.info("Starting article collection...")

        all_articles: List[Article] = []
        source_items = list(self.sources.items())

        if _fetch_parallel_enabled():
            max_workers = max(1, _logging_env_int("FETCH_MAX_WORKERS", 8))
            logger.info("Fetching sources in parallel (FETCH_MAX_WORKERS=%s)", max_workers)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map = {}
                for source_name, source_config in source_items:
                    sess = requests.Session()
                    sess.headers.update(DEFAULT_HEADERS)
                    fut = pool.submit(self._fetch_from_source, source_name, source_config, sess)
                    future_map[fut] = source_name
                for fut in as_completed(future_map):
                    source_name = future_map[fut]
                    try:
                        articles = fut.result()
                    except Exception as e:
                        logger.error("Error fetching from %s: %s", source_name, e)
                        continue
                    all_articles.extend(articles)
                    logger.info("Fetched %s articles from %s", len(articles), source_name)
        else:
            for source_name, source_config in source_items:
                try:
                    logger.info("Fetching articles from %s", source_name)
                    articles = self._fetch_from_source(source_name, source_config)
                    all_articles.extend(articles)
                    logger.info("Fetched %s articles from %s", len(articles), source_name)
                except Exception as e:
                    logger.error("Error fetching from %s: %s", source_name, e)
        
        deduped = self._dedupe_articles(all_articles)
        apply_filter = filter_by_date and bool(date)
        if apply_filter:
            keep_unknown = os.getenv("DATE_FILTER_KEEP_UNKNOWN", "true").strip().lower() not in (
                "0",
                "false",
                "no",
            )
            deduped, stats = filter_articles_by_date(
                deduped, date, keep_if_unknown=keep_unknown
            )
            logger.info("Date filter stats: %s", stats)

        deduped = self._sort_articles_by_recency(deduped)

        pre_seen_count = len(deduped)
        if self.seen_store:
            deduped, _st = self.seen_store.filter_articles(deduped)
            if pre_seen_count > 0 and len(deduped) == 0:
                logger.warning(
                    "All %s candidates were skipped by cross-run dedupe. "
                    "Lower URL_COOLDOWN_DAYS / TITLE_COOLDOWN_DAYS or clear SEEN_ARTICLES_PATH (%s).",
                    pre_seen_count,
                    self.seen_store.path,
                )

        self.articles = deduped
        logger.info(
            "Total articles collected (after dedupe%s%s): %s",
            "/date filter" if apply_filter else "",
            "/cross-run memory" if self.seen_store else "",
            len(self.articles),
        )
        return self.articles

    def _dedupe_articles(self, articles: List[Article]) -> List[Article]:
        """Remove duplicates by normalized URL, URL slug, title fingerprint, and core title key."""
        seen_norm_urls = set()
        seen_title_fp = set()
        seen_slugs = set()
        seen_cores = set()
        out: List[Article] = []
        for a in articles:
            nu = normalize_url(a.url or "")
            tfp = title_fingerprint(a.title or "")
            sk = url_slug_key(a.url or "")
            ck = core_title_key(a.title or "")
            if nu and nu in seen_norm_urls:
                continue
            if sk and sk in seen_slugs:
                continue
            if tfp and tfp in seen_title_fp:
                continue
            if ck and ck in seen_cores:
                continue
            if nu:
                seen_norm_urls.add(nu)
            if sk:
                seen_slugs.add(sk)
            if tfp:
                seen_title_fp.add(tfp)
            if ck:
                seen_cores.add(ck)
            out.append(a)
        return out
    
    def _fetch_from_source(
        self,
        source_name: str,
        source_config: Dict,
        http_session: Optional[requests.Session] = None,
    ) -> List[Article]:
        """
        Fetch articles from a specific source with optimization.

        Args:
            source_name: Name of the source
            source_config: Configuration for the source
            http_session: Optional session (each parallel worker uses its own Session)

        Returns:
            List of Article objects from the source
        """
        http = http_session if http_session is not None else self.http
        try:
            url = source_config['url']
            parser_type = source_config['parser']
            limit = source_config.get('limit', 10)
            filter_keywords = source_config.get('filter_keywords', [])
            
            if parser_type == 'hackernews_api':
                # Use HN API for better filtering
                response = self._with_retries(lambda: http.get(url, timeout=REQUEST_TIMEOUT))
                response.raise_for_status()
                return self._parse_hackernews_api(response.json(), source_name, limit)
            elif parser_type == 'web_scrape':
                # Web scraping for sites without RSS feeds
                response = self._with_retries(lambda: http.get(url, timeout=REQUEST_TIMEOUT))
                response.raise_for_status()
                articles = self._parse_web_scrape(response.text, source_name, limit, url)
                
                # Apply keyword filtering if specified
                if filter_keywords:
                    articles = self._filter_by_keywords(articles, filter_keywords)
                
                return articles
            else:
                # Standard RSS parsing
                response = self._with_retries(lambda: http.get(url, timeout=REQUEST_TIMEOUT))
                response.raise_for_status()
                
                if parser_type == 'arxiv':
                    articles = self._parse_arxiv_feed(response.text, source_name, limit)
                elif parser_type == 'rss':
                    articles = self._parse_rss_feed(response.text, source_name, limit)
                else:
                    # Legacy support
                    if 'arxiv' in source_name:
                        articles = self._parse_arxiv_feed(response.text, source_name, limit)
                    elif 'hackernews' in source_name:
                        articles = self._parse_hackernews_feed(response.text, source_name, limit)
                    elif 'techcrunch' in source_name:
                        articles = self._parse_techcrunch_feed(response.text, source_name, limit)
                    else:
                        return []
                
                # Apply keyword filtering if specified
                if filter_keywords:
                    articles = self._filter_by_keywords(articles, filter_keywords)
                
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return []
    
    def _parse_arxiv_feed(self, feed_content: str, source_name: str = 'arXiv', limit: int = 20) -> List[Article]:
        """Parse arXiv RSS feed for AI-related papers."""
        articles = []
        feed = feedparser.parse(feed_content)
        
        for entry in feed.entries[:limit]:  # Use dynamic limit
            # Filter for AI-related content
            if any(keyword in entry.title.lower() for keyword in ['ai', 'artificial intelligence', 'machine learning', 'neural']):
                article = Article(
                    title=entry.title,
                    url=entry.link,
                    source=source_name,
                    published_date=entry.published,
                    content=entry.summary
                )
                articles.append(article)
        
        return articles
    
    def _parse_hackernews_feed(self, feed_content: str, source_name: str = 'Hacker News', limit: int = 50) -> List[Article]:
        """Parse Hacker News RSS feed for AI-related posts."""
        articles = []
        feed = feedparser.parse(feed_content)
        
        for entry in feed.entries[:limit]:  # Check entries for AI content
            # Filter for AI-related content
            if any(keyword in entry.title.lower() for keyword in ['ai', 'artificial intelligence', 'machine learning', 'gpt', 'openai', 'anthropic']):
                article = Article(
                    title=entry.title,
                    url=entry.link,
                    source=source_name,
                    published_date=entry.published,
                    content=entry.summary
                )
                articles.append(article)
        
        return articles
    
    def _parse_techcrunch_feed(self, feed_content: str, source_name: str = 'TechCrunch', limit: int = 20) -> List[Article]:
        """Parse TechCrunch AI feed."""
        articles = []
        feed = feedparser.parse(feed_content)
        
        for entry in feed.entries[:limit]:
            article = Article(
                title=entry.title,
                url=entry.link,
                source=source_name,
                published_date=entry.published,
                content=entry.summary
            )
            articles.append(article)
        
        return articles
    
    def _parse_rss_feed(self, feed_content: str, source_name: str, limit: int = 20) -> List[Article]:
        """Parse generic RSS feed."""
        articles = []
        feed = feedparser.parse(feed_content)
        
        for entry in feed.entries[:limit]:
            article = Article(
                title=entry.title,
                url=entry.link,
                source=source_name,
                published_date=getattr(entry, 'published', ''),
                content=getattr(entry, 'summary', '')[:200]  # Truncate for cost optimization
            )
            articles.append(article)
        
        return articles
    
    def _parse_hackernews_api(self, api_response: dict, source_name: str, limit: int = 5) -> List[Article]:
        """Parse Hacker News API response."""
        articles = []

        for hit in api_response.get('hits', [])[:limit]:
            title = hit.get('title')
            url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if not title or not url:
                continue

            article = Article(
                title=title,
                url=url,
                source=source_name,
                published_date=hit.get('created_at', ''),
                content=(hit.get('comment_text') or '')[:200]
            )
            articles.append(article)

        return articles
    
    def _parse_web_scrape(self, html_content: str, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse web pages for articles using BeautifulSoup."""
        articles = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Different parsing strategies based on source (isolated so one failure does not blank others)
            try:
                if 'google' in source_name.lower():
                    articles = self._parse_google_research(soup, source_name, limit, base_url)
                elif 'deepmind' in source_name.lower():
                    articles = self._parse_deepmind(soup, source_name, limit, base_url)
                elif 'gemini' in source_name.lower():
                    articles = self._parse_gemini(soup, source_name, limit, base_url)
                elif 'anthropic' in source_name.lower():
                    articles = self._parse_anthropic(soup, source_name, limit, base_url)
                elif 'mistral' in source_name.lower():
                    articles = self._parse_mistral(soup, source_name, limit, base_url)
                elif 'qwen' in source_name.lower():
                    articles = self._parse_qwen(soup, source_name, limit, base_url)
                elif 'asml' in source_name.lower():
                    articles = self._parse_asml(soup, source_name, limit, base_url)
                else:
                    articles = self._parse_generic_web(soup, source_name, limit, base_url)
            except Exception as inner_exc:
                logger.warning(
                    "Site-specific parser failed for %s (%s); returning 0 articles from this scrape",
                    source_name,
                    inner_exc,
                )
                articles = []

            if not articles:
                logger.warning(
                    "Web scrape returned no articles for %s — page layout may have changed",
                    source_name,
                )
            
        except Exception as e:
            logger.error(f"Error parsing web content for {source_name}: {e}")
        
        return articles
    
    def _parse_google_research(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse Google Research blog."""
        articles = []
        
        # Look for article links with more specific targeting
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 5]:  # Get more to filter
            href = link.get('href')
            title = link.get_text(strip=True)
            
            # Filter for actual article links
            if (href and title and len(title) > 10 and 
                not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']) and
                not any(skip in title.lower() for skip in ['skip', 'menu', 'navigation', 'cookie', 'privacy'])):
                
                url = urljoin(base_url, href)
                
                # Only include if it looks like an article
                if any(keyword in title.lower() for keyword in ['research', 'ai', 'machine learning', 'neural', 'model']):
                    article = Article(
                        title=title,
                        url=url,
                        source=source_name,
                        content=title
                    )
                    articles.append(article)
                    
                    if len(articles) >= limit:
                        break
        
        return articles
    
    def _parse_deepmind(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse DeepMind blog."""
        articles = []
        
        # Look for article links
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 3]:
            href = link.get('href')
            title = link.get_text(strip=True)

            href_l = (href or "").lower()
            title_l = (title or "").lower()

            if any(skip in href_l for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                continue
            if any(skip in title_l for skip in ['privacy', 'cookie', 'careers', 'about', 'contact', 'terms']):
                continue
            
            if href and title and len(title) > 10:
                url = urljoin(base_url, href)
                
                article = Article(
                    title=title,
                    url=url,
                    source=source_name,
                    content=title
                )
                articles.append(article)
                
                if len(articles) >= limit:
                    break
        
        return articles
    
    def _parse_gemini(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse Gemini blog."""
        articles = []
        
        # Look for article links
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 3]:
            href = link.get('href')
            title = link.get_text(strip=True)
            
            href_l = (href or "").lower()
            title_l = (title or "").lower()

            if any(skip in href_l for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                continue
            if any(skip in title_l for skip in ['privacy', 'cookie', 'careers', 'about', 'contact', 'terms']):
                continue
            
            if href and title and len(title) > 10:

                url = urljoin(base_url, href)
                
                article = Article(
                    title=title,
                    url=url,
                    source=source_name,
                    content=title
                )
                articles.append(article)
                
                if len(articles) >= limit:
                    break
        
        return articles
    
    def _parse_anthropic(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse Anthropic news."""
        articles = []
        
        # Look for article cards and headlines
        # Anthropic uses specific card structures for their news
        article_cards = soup.find_all(['article', 'div'], class_=lambda x: x and any(word in x.lower() for word in ['card', 'article', 'news', 'post']))
        
        # Also look for links that might be articles
        article_links = soup.find_all('a', href=True)
        
        # Combine both approaches
        potential_articles = []
        
        # Process cards first
        for card in article_cards:
            # Look for headlines within cards
            headlines = card.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for headline in headlines:
                title = headline.get_text(strip=True)
                if title and len(title) > 10:
                    # Find the closest link
                    link = headline.find_parent('a') or headline.find('a')
                    href = link.get('href') if link else None
                    if href:
                        potential_articles.append((title, href))
        
        # Process direct links
        for link in article_links:
            href = link.get('href')
            title = link.get_text(strip=True)
            
            # Filter out navigation and non-article links
            if (href and title and len(title) > 10 and
                not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']) and
                not any(skip in title.lower() for skip in ['skip', 'menu', 'navigation', 'cookie', 'privacy', 'press@', 'support.'])):
                
                potential_articles.append((title, href))
        
        # Remove duplicates and process
        seen_titles = set()
        for raw_title, href in potential_articles:
            title = clean_scraped_news_title(raw_title)
            if not title or len(title) <= 10:
                continue
            if title not in seen_titles and len(articles) < limit:
                seen_titles.add(title)

                url = urljoin(base_url, href)

                # Only include if it looks like a real article (exclude contact/email links)
                if (any(keyword in title.lower() for keyword in ['claude', 'anthropic', 'introducing', 'announcement', 'release', 'model', 'ai']) and
                    not any(skip in title.lower() for skip in ['press@', 'support.', 'mailto:', '@anthropic.com']) and
                    not any(skip in href.lower() for skip in ['mailto:', 'tel:'])):
                    article = Article(
                        title=title,
                        url=url,
                        source=source_name,
                        content=title
                    )
                    articles.append(article)
        
        return articles
    
    def _parse_mistral(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse Mistral AI news."""
        articles = []
        
        # Look for article links
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 3]:
            href = link.get('href')
            title = link.get_text(strip=True)

            href_l = (href or "").lower()
            title_l = (title or "").lower()

            if any(skip in href_l for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                continue
            if any(skip in title_l for skip in ['privacy', 'cookie', 'careers', 'about', 'contact', 'terms']):
                continue
            
            if href and title and len(title) > 10:
                url = urljoin(base_url, href)
                
                article = Article(
                    title=title,
                    url=url,
                    source=source_name,
                    content=title
                )
                articles.append(article)
                
                if len(articles) >= limit:
                    break
        
        return articles
    
    def _parse_qwen(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse Qwen blog."""
        articles = []
        
        # Look for article links with better filtering
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 5]:
            href = link.get('href')
            title = link.get_text(strip=True)
            
            # Filter for actual article links
            if (href and title and len(title) > 10 and 
                not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']) and
                not any(skip in title.lower() for skip in ['skip', 'menu', 'navigation', 'cookie', 'privacy'])):
                
                url = urljoin(base_url, href)
                
                # Only include if it looks like an article
                if any(keyword in title.lower() for keyword in ['qwen', 'model', 'ai', 'release', 'update']):
                    article = Article(
                        title=title,
                        url=url,
                        source=source_name,
                        content=title
                    )
                    articles.append(article)
                    
                    if len(articles) >= limit:
                        break
        
        return articles
    
    def _parse_asml(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse ASML press releases."""
        articles = []
        
        # Look for article links with better filtering
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 5]:
            href = link.get('href')
            title = link.get_text(strip=True)
            
            # Filter for actual article links
            if (href and title and len(title) > 10 and 
                not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']) and
                not any(skip in title.lower() for skip in ['skip', 'menu', 'navigation', 'cookie', 'privacy'])):
                
                url = urljoin(base_url, href)
                
                # Only include if it looks like a press release or AI-related
                if any(keyword in title.lower() for keyword in ['press', 'release', 'news', 'ai', 'semiconductor', 'chip']):
                    article = Article(
                        title=title,
                        url=url,
                        source=source_name,
                        content=title
                    )
                    articles.append(article)
                    
                    if len(articles) >= limit:
                        break
        
        return articles
    
    def _parse_generic_web(self, soup, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Generic web parsing for unknown sites."""
        articles = []
        
        # Look for article links
        article_links = soup.find_all('a', href=True)
        
        for link in article_links[:limit * 3]:
            href = link.get('href')
            title = link.get_text(strip=True)

            href_l = (href or "").lower()
            title_l = (title or "").lower()

            if any(skip in href_l for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                continue
            if any(skip in title_l for skip in ['privacy', 'cookie', 'careers', 'about', 'contact', 'terms']):
                continue
            
            if href and title and len(title) > 10:
                url = urljoin(base_url, href)
                
                article = Article(
                    title=title,
                    url=url,
                    source=source_name,
                    content=title
                )
                articles.append(article)
                
                if len(articles) >= limit:
                    break
        
        return articles
    
    def _filter_by_keywords(self, articles: List[Article], keywords: List[str]) -> List[Article]:
        """Filter articles by keywords in title or content."""
        filtered_articles = []
        
        for article in articles:
            text_to_search = f"{article.title} {article.content or ''}".lower()
            if any(keyword.lower() in text_to_search for keyword in keywords):
                filtered_articles.append(article)
        
        return filtered_articles

    def _maybe_enrich_article_html(self, article: Article) -> None:
        """Optional: fetch article HTML when RSS/snippet text is too thin (bounded; default off)."""
        if os.getenv("ENRICH_ARTICLE_HTML", "").strip().lower() not in ("1", "true", "yes", "on"):
            return
        max_per_run = max(0, _logging_env_int("ENRICH_MAX_PER_RUN", 12))
        if self._enrich_fetch_count >= max_per_run:
            return
        min_chars = max(50, _logging_env_int("ENRICH_MIN_PLAINTEXT_CHARS", 360))
        excerpt = (article.content or "").strip()
        if len(excerpt) >= min_chars:
            return
        url = (article.url or "").strip()
        if not url.startswith(("http://", "https://")):
            return
        base_url = url.split("?", 1)[0].lower()
        if base_url.endswith(".pdf"):
            return

        max_bytes = max(50_000, _logging_env_int("ENRICH_MAX_RESPONSE_BYTES", 800_000))
        max_plain = max(2_000, _logging_env_int("ENRICH_MAX_PLAINTEXT_CHARS", 12_000))

        try:
            self._enrich_fetch_count += 1
            response = self._with_retries(lambda: self.http.get(url, timeout=REQUEST_TIMEOUT))
            response.raise_for_status()
            raw = response.content
            if len(raw) > max_bytes:
                logger.debug("Enrich skipped (too large): %s", url[:96])
                return
            ctype = (response.headers.get("Content-Type") or "").lower()
            if not any(x in ctype for x in ("html", "text/plain", "xml", "application/xhtml")):
                return
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = text.strip()[:max_plain]
            if len(text) > len(excerpt):
                article.content = text
                logger.info("Enriched article body from HTML (%s chars): %s", len(text), url[:80])
        except Exception as exc:
            logger.debug("HTML enrich failed for %s: %s", url[:96], exc)

    def summarize_articles(self) -> List[Article]:
        """
        Summarize collected articles using the configured OpenAI chat model.

        Returns:
            List of Article objects with summaries
        """
        logger.info("Starting article summarization...")
        
        summarized_articles = []
        to_process = list(self.articles)
        cap = summarize_max_articles_from_env()
        if cap is not None and len(to_process) > cap:
            logger.warning(
                "Summarization cap: processing %s/%s articles (set SUMMARIZE_MAX_ARTICLES to adjust)",
                cap,
                len(to_process),
            )
            to_process = to_process[:cap]

        for i, article in enumerate(to_process):
            try:
                logger.info(f"Summarizing article {i+1}/{len(to_process)}: {article.title[:50]}...")

                self._maybe_enrich_article_html(article)

                summary = self._summarize_with_gpt(article)
                article.summary = summary.strip() if isinstance(summary, str) and summary.strip() else "Not specified"
                summarized_articles.append(article)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error summarizing article '{article.title}': {e}")
                # Add article without summary
                summarized_articles.append(article)
        
        self.summarized_articles = summarized_articles
        logger.info("Summarized %s articles", len(self.summarized_articles))
        return self.summarized_articles
    
    def _summarize_with_gpt(self, article: Article) -> str:
        """
        Summarize a single article using GPT.
        
        Args:
            article: Article object to summarize
            
        Returns:
            Summary string
        """
        content = article.content or article.title
        
        prompt = f"""
        Summarize this item for experienced AI practitioners (engineers, researchers, PMs) in 2–3 sentences.
        Lead with concrete facts: what changed, who it affects, numbers/benchmarks/API/model IDs when present.
        Separate verifiable claims from opinion in the source; do not invent benchmarks or quotes.
        If the excerpt is thin, say what is missing in one short clause. Output ONLY the summary.

        <article>
        Title: {article.title}
        Source: {article.source}
        Content: {content[:1000]}
        </article>

        Summary:
        """.strip()
        # 1000 = Limit content length
        
        try:
            tok_kw = completion_output_kw(self.summary_model, 120)

            def _call():
                return self.client.chat.completions.create(
                    model=self.summary_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You summarize AI industry news for practitioners. Be precise and factual; prefer "
                                "specifics (models, APIs, datasets, metrics, release dates) over hype. "
                                "Do not speculate or fabricate. If the excerpt lacks detail, say so briefly. "
                                "Exactly 2–3 sentences."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15,
                    **tok_kw,
                )

            response = self._with_retries(_call)
            log_openai_usage(logger, response, "summarize")
            self._accumulate_usage(response)

            text = (response.choices[0].message.content or "").strip()
            if not text:
                return "Not specified"
            return text
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Summary unavailable: {article.title}"
    
    def rank_top_articles(self, top_n: int = 10) -> List[Article]:
        """
        Rank and select the top N articles using the configured OpenAI model (structured JSON).

        Args:
            top_n: Number of top articles to select

        Returns:
            List of top ranked Article objects
        """
        logger.info(f"Ranking top {top_n} articles...")
        
        if not self.summarized_articles:
            logger.error("No summarized articles available for ranking")
            return []

        total = len(self.summarized_articles)
        effective_top_n = min(top_n, total)
        
        # Prepare summaries for ranking
        summaries_text = ""
        for i, article in enumerate(self.summarized_articles):
            summaries_text += f"{i+1}. {article.title}\n"
            summaries_text += f"   Source: {article.source}\n"
            summary = article.summary or "Not specified"
            summaries_text += f"   Summary: {summary[:350]}\n\n"
        
        ranking_prompt = f"""
Here are AI news article summaries (1-based index shown before each title).

Choose and rank the {effective_top_n} most important for people shipping or researching AI daily.
Prioritize: substantive model/tool/API releases, rigorous research with clear results, infra/runtime changes,
policy/safety with operational impact, and major commercial moves — over generic trend pieces or rewrites.

Return a single JSON object with this exact shape (no markdown fences, no extra keys):
{{"ranked_article_numbers":[<int>, ...]}}

Rules:
- The array must contain exactly {effective_top_n} distinct integers.
- Each integer must be between 1 and {total} (inclusive).
- Order matters: first element = most important article index.

Articles:
{summaries_text}
""".strip()

        system_msg = (
            f"You curate a daily briefing for AI practitioners. Pick stories that change what readers build, "
            f"evaluate, or comply with next week. Prefer signal over repetitive announcements. "
            f"Respond with JSON only: {{\"ranked_article_numbers\": [<ints>]}} — exactly {effective_top_n} "
            f"distinct integers from 1..{total}, most important first."
        )

        tok_kw = completion_output_kw(self.rank_model, 256)

        def _rank_call(extra_kw: Optional[dict] = None):
            kwargs = {
                "model": self.rank_model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": ranking_prompt},
                ],
                "temperature": 0.0,
                **tok_kw,
            }
            if extra_kw:
                kwargs.update(extra_kw)
            return self.client.chat.completions.create(**kwargs)

        try:
            try:
                response = self._with_retries(lambda: _rank_call({"response_format": {"type": "json_object"}}))
            except BadRequestError as e:
                logger.warning(
                    "Ranking: json_object response_format not accepted (%s); retrying without response_format",
                    e,
                )
                response = self._with_retries(lambda: _rank_call())

            log_openai_usage(logger, response, "rank")
            self._accumulate_usage(response)

            response_text = (response.choices[0].message.content or "").strip()
            parsed = ranked_indices_from_llm(
                response_text,
                effective_top_n=effective_top_n,
                total_articles=total,
            )

            if parsed.method == "fallback_first_n" or len(parsed.indices_0based) != effective_top_n:
                logger.error(
                    "Ranking fallback: method=%s parsed_len=%s want=%s — using first %s articles",
                    parsed.method,
                    len(parsed.indices_0based),
                    effective_top_n,
                    effective_top_n,
                )
                self.top_articles = self.summarized_articles[:effective_top_n]
                return self.top_articles

            top_articles = [
                self.summarized_articles[i]
                for i in parsed.indices_0based
                if i < len(self.summarized_articles)
            ]
            if len(top_articles) != effective_top_n:
                logger.error(
                    "Ranking produced %s articles after index resolution (want %s) — fallback to first N",
                    len(top_articles),
                    effective_top_n,
                )
                self.top_articles = self.summarized_articles[:effective_top_n]
                return self.top_articles

            self.top_articles = top_articles
            logger.info(
                "Selected top %s articles (ranking_parse_method=%s)",
                len(self.top_articles),
                parsed.method,
            )
            return self.top_articles

        except Exception as e:
            logger.error(f"Error ranking articles: {e}")
            self.top_articles = self.summarized_articles[:effective_top_n]
            return self.top_articles
    
    def output_results(self, date: Optional[str] = None, output_format: str = 'markdown') -> str:
        """
        Output the results in the specified format.
        
        Args:
            date: Date string for filename
            output_format: Output format ('markdown', 'notion', 'email', 'slack')
            
        Returns:
            Output content as string
        """
        if not self.top_articles:
            logger.error("No top articles available for output")
            return ""
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if output_format == 'markdown':
            return self._output_markdown(date)
        elif output_format == 'notion':
            return self._output_notion(date)
        elif output_format == 'email':
            return self._output_email(date)
        elif output_format == 'slack':
            return self._output_slack(date)
        else:
            logger.error(f"Unsupported output format: {output_format}")
            return ""
    
    def _output_markdown(self, date: str) -> str:
        """Generate markdown output."""
        filename = f"top_ai_news_{date}.md"
        
        content = self._generate_markdown_content(date)
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Markdown output saved to {filename}")
        return content
    
    def _output_notion(self, date: str) -> str:
        """Output via Notion."""
        from utils import NotionClient
        
        notion_client = NotionClient()
        title = f"Top AI News - {date}"
        
        # Generate markdown content
        content = self._generate_markdown_content(date)
        
        # Create page and capture URL
        page_url = notion_client.create_page(title, content, date)
        if page_url:
            logger.info(f"Successfully posted to Notion: {title}")
            # Store the URL for notifications
            self.last_notion_url = page_url
            
        else:
            logger.error("Failed to post to Notion")
        
        return content
    
    def _output_email(self, date: str) -> str:
        """Output via email."""
        from utils import EmailClient
        
        email_client = EmailClient()
        subject = f"Top AI News - {date}"
        
        # Generate markdown content
        content = self._generate_markdown_content(date)
        
        if email_client.send_email(subject, content, date):
            logger.info(f"Successfully sent email: {subject}")
            return content
        else:
            logger.error("Failed to send email")
            return ""

    def _output_slack(self, date: str) -> str:
        """Output via Slack (Incoming Webhook)."""
        from utils import SlackClient

        MAX_LEN = 35000  # conservative buffer
        content = self._generate_markdown_content(date)
        if len(content) > MAX_LEN:
            logger.warning(f"Content exceeds Slack message length limit ({MAX_LEN} chars). Truncating...")
            content = content[:MAX_LEN] + "\n\n...(truncated)"

        slack = SlackClient()
        ok = slack.send_message(content)

        if ok:
            logger.info("Successfully posted to Slack")
            return content
        else:
            logger.error("Failed to post to Slack")
            return ""
    
    def _generate_markdown_content(self, date: str) -> str:
        """Generate markdown content for output."""
        content = f"# Top AI News - {date}\n\n"
        content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"## Top {len(self.top_articles)} AI Updates of the Day\n\n"
        
        for i, article in enumerate(self.top_articles, 1):
            content += f"### {i}. {article.title}\n\n"
            content += f"**Source:** {article.source}\n\n"
            content += f"**Summary:** {article.summary or 'Not specified'}\n\n"
            content += f"**Link:** {article.url}\n\n"
            content += "---\n\n"
        
        return content
    
    def run_daily_pipeline(
        self,
        date: Optional[str] = None,
        output_format: str = 'markdown',
        top_n: Optional[int] = None,
        *,
        filter_by_date: bool = False,
        dry_run: bool = False,
    ) -> str:
        """
        Run the complete daily pipeline.

        Args:
            date: Optional date string
            output_format: Output format
            top_n: Number of articles to rank/output (default: TOP_ARTICLES env or 10)
            filter_by_date: Pass through to get_articles when True
            dry_run: Collect and filter only; skip LLM, ranking, outputs, and seen-store updates.

        Returns:
            Output content
        """
        logger.info("Starting daily AI news pipeline...")
        self._usage_prompt_tokens = 0
        self._usage_completion_tokens = 0
        self.last_notion_url = None
        self._enrich_fetch_count = 0

        effective_top_n = top_n if top_n is not None else top_n_from_env(10)

        self.get_articles(date, filter_by_date=filter_by_date)

        if dry_run:
            logger.info(
                "Dry run: %s articles after filters — skipping LLM, ranking, outputs, and seen-store updates.",
                len(self.articles),
            )
            self.summarized_articles = []
            self.top_articles = []
            logger.info(
                "Dry run completed (OpenAI usage — prompt_tokens=%s completion_tokens=%s)",
                self._usage_prompt_tokens,
                self._usage_completion_tokens,
            )
            return ""

        if not self.articles:
            logger.warning(
                "No articles after collection and filters — skipping summarization, ranking, and OpenAI calls."
            )
            self.summarized_articles = []
            self.top_articles = []
            logger.info(
                "Pipeline stopped early (OpenAI usage — prompt_tokens=%s completion_tokens=%s)",
                self._usage_prompt_tokens,
                self._usage_completion_tokens,
            )
            return ""

        self.summarize_articles()
        self.rank_top_articles(effective_top_n)

        output = self.output_results(date, output_format)

        record_scope = (os.getenv("SEEN_RECORD_SCOPE") or "digest").strip().lower()
        to_record = (
            self.summarized_articles if record_scope == "summarized" else self.top_articles
        )

        if (
            self.seen_store
            and to_record
            and self._digest_output_succeeded(output_format, output)
        ):
            self.seen_store.record_processed_batch(to_record)

        logger.info(
            "Daily pipeline completed (OpenAI usage — prompt_tokens=%s completion_tokens=%s)",
            self._usage_prompt_tokens,
            self._usage_completion_tokens,
        )
        return output


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def main():
    """Main entry point for the AI News Agent."""
    parser = argparse.ArgumentParser(description='AI News Agent - Daily AI News Aggregator')
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help=(
            'Calendar date YYYY-MM-DD for labeling output files and optional filtering. '
            'Collection still pulls current feeds from sources; use --filter-by-date (or ARTICLE_DATE_FILTER) '
            'to restrict to articles whose publication date matches this UTC day.'
        ),
    )
    parser.add_argument('--output', choices=['markdown', 'notion', 'email', 'slack'], default='markdown', 
                       help='Output format (default: markdown)')
    parser.add_argument(
        '--top-n',
        type=int,
        default=None,
        help='How many articles to rank and output (default: TOP_ARTICLES env or 10)',
    )
    parser.add_argument(
        '--filter-by-date',
        action='store_true',
        help='Keep only articles whose published timestamp falls on --date (UTC). '
        'Default off; can also set ARTICLE_DATE_FILTER=true.',
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--schedule', action='store_true', help='Run scheduled daily')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and filter articles only; skip OpenAI, ranking, and all outputs (Notion/Slack/email/Markdown file). '
        'No seen-store updates.',
    )

    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    agent = AINewsAgent()

    filter_by_date = args.filter_by_date or _env_truthy("ARTICLE_DATE_FILTER")
    
    if args.schedule:
        logger.info("Starting scheduled daily runs...")
        schedule.every().day.at("09:00").do(
            lambda: agent.run_daily_pipeline(
                None,
                args.output,
                args.top_n,
                filter_by_date=filter_by_date,
            )
        )
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Run once
        output = agent.run_daily_pipeline(
            args.date,
            args.output,
            args.top_n,
            filter_by_date=filter_by_date,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(
                "\nDry run finished: feeds were fetched and filtered only.\n"
                "Nothing was posted to Notion, Slack, or email, and no Markdown file was written.\n"
                "To publish to Notion, run without --dry-run, e.g.:\n"
                "  python ai_news_agent.py --output notion\n"
                "Or use run_agent.py / daily_scheduler.py for your usual automated post.\n"
            )
        else:
            print(f"\n{output}")


if __name__ == "__main__":
    main() 