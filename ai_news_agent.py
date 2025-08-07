#!/usr/bin/env python3
"""
AI News Agent - Daily AI News Aggregator and Summarizer

This script fetches AI-related news from multiple sources, summarizes them using GPT-4,
ranks the most important stories, and outputs the top 10 AI updates of the day.

Author: AI News Agent
Date: 2024
"""

import os
import sys
import logging
import argparse
import json
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Third-party imports
import openai
from dotenv import load_dotenv
import schedule
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_news_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

# Get organization and project IDs for project-based API keys
OPENAI_ORGANIZATION_ID = os.getenv('OPENAI_ORGANIZATION_ID')
OPENAI_PROJECT_ID = os.getenv('OPENAI_PROJECT_ID')


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
                'url': 'https://deepmind.google/discover/blog/',
                'parser': 'web_scrape',
                'limit': 5
            },
            'gemini': {
                'url': 'https://ai.google.dev/',
                'parser': 'web_scrape',
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
    
    def get_articles(self, date: Optional[str] = None) -> List[Article]:
        """
        Fetch articles from all configured sources.
        
        Args:
            date: Optional date string in YYYY-MM-DD format
            
        Returns:
            List of Article objects
        """
        logger.info("Starting article collection...")
        
        all_articles = []
        
        for source_name, source_config in self.sources.items():
            try:
                logger.info(f"Fetching articles from {source_name}")
                articles = self._fetch_from_source(source_name, source_config)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {source_name}")
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
        
        # Skip date filtering for now (include recent articles by default)
        # Focus on getting high-quality recent content instead
        
        self.articles = all_articles
        logger.info(f"Total articles collected: {len(self.articles)}")
        return self.articles
    
    def _fetch_from_source(self, source_name: str, source_config: Dict) -> List[Article]:
        """
        Fetch articles from a specific source with optimization.
        
        Args:
            source_name: Name of the source
            source_config: Configuration for the source
            
        Returns:
            List of Article objects from the source
        """
        try:
            url = source_config['url']
            parser_type = source_config['parser']
            limit = source_config.get('limit', 10)
            filter_keywords = source_config.get('filter_keywords', [])
            
            if parser_type == 'hackernews_api':
                # Use HN API for better filtering
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return self._parse_hackernews_api(response.json(), source_name, limit)
            elif parser_type == 'web_scrape':
                # Web scraping for sites without RSS feeds
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                articles = self._parse_web_scrape(response.text, source_name, limit, url)
                
                # Apply keyword filtering if specified
                if filter_keywords:
                    articles = self._filter_by_keywords(articles, filter_keywords)
                
                return articles
            else:
                # Standard RSS parsing
                response = requests.get(url, timeout=30)
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
            if hit.get('url') and hit.get('title'):
                article = Article(
                    title=hit['title'],
                    url=hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                    source=source_name,
                    published_date=hit.get('created_at', ''),
                    content=hit.get('comment_text', '')[:200] if hit.get('comment_text') else ''
                )
                articles.append(article)
        
        return articles
    
    def _parse_web_scrape(self, html_content: str, source_name: str, limit: int, base_url: str) -> List[Article]:
        """Parse web pages for articles using BeautifulSoup."""
        articles = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Different parsing strategies based on source
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
                # Generic parsing
                articles = self._parse_generic_web(soup, source_name, limit, base_url)
            
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
                
                # Make URL absolute
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
            
            if href and title and len(title) > 10:
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
            
            if href and title and len(title) > 10:
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
        for title, href in potential_articles:
            if title not in seen_titles and len(articles) < limit:
                seen_titles.add(title)
                
                # Make URL absolute
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
            
            if href and title and len(title) > 10:
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
                
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
                
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
            
            if href and title and len(title) > 10:
                if href.startswith('/'):
                    url = base_url.rstrip('/') + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = base_url.rstrip('/') + '/' + href
                
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
            text_to_search = (article.title + ' ' + article.content).lower()
            if any(keyword.lower() in text_to_search for keyword in keywords):
                filtered_articles.append(article)
        
        return filtered_articles
    
    def summarize_articles(self) -> List[Article]:
        """
        Summarize all collected articles using GPT-4.
        
        Returns:
            List of Article objects with summaries
        """
        logger.info("Starting article summarization...")
        
        summarized_articles = []
        
        for i, article in enumerate(self.articles):
            try:
                logger.info(f"Summarizing article {i+1}/{len(self.articles)}: {article.title[:50]}...")
                
                summary = self._summarize_with_gpt(article)
                article.summary = summary
                summarized_articles.append(article)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error summarizing article '{article.title}': {e}")
                # Add article without summary
                summarized_articles.append(article)
        
        self.summarized_articles = summarized_articles
        logger.info(f"Summarized {len(self.summarized_articles)} articles")
        return self.summarized_articles
    
    def _summarize_with_gpt(self, article: Article) -> str:
        """
        Summarize a single article using GPT-4.
        
        Args:
            article: Article object to summarize
            
        Returns:
            Summary string
        """
        content = article.content or article.title
        
        prompt = f"""
        Please provide a concise 2-3 sentence summary of this AI-related article. 
        Focus on the key technical developments, business implications, or research breakthroughs.
        
        Title: {article.title}
        Source: {article.source}
        Content: {content[:1000]}  # Limit content length
        
        Summary:
        """
        
        try:
            # Create client with organization header if available
            client_kwargs = {}
            if OPENAI_ORGANIZATION_ID:
                client_kwargs['organization'] = OPENAI_ORGANIZATION_ID
                
            client = openai.OpenAI(**client_kwargs)
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Much cheaper model
                messages=[
                    {"role": "system", "content": "You are an expert AI researcher and technology analyst. Provide clear, concise summaries of AI news articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,  # Reduced tokens for cost optimization
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Summary unavailable: {article.title}"
    
    def rank_top_articles(self, top_n: int = 10) -> List[Article]:
        """
        Rank and select the top N most important articles using GPT-4.
        
        Args:
            top_n: Number of top articles to select
            
        Returns:
            List of top ranked Article objects
        """
        logger.info(f"Ranking top {top_n} articles...")
        
        if not self.summarized_articles:
            logger.error("No summarized articles available for ranking")
            return []
        
        # Prepare summaries for ranking
        summaries_text = ""
        for i, article in enumerate(self.summarized_articles):
            summaries_text += f"{i+1}. {article.title}\n"
            summaries_text += f"   Source: {article.source}\n"
            summaries_text += f"   Summary: {article.summary}\n\n"
        
        ranking_prompt = f"""
        Here are AI news summaries from today. Choose and rank the {top_n} most important ones 
        for AI researchers, builders, and investors. Consider:
        - Technical significance and innovation
        - Business and market impact
        - Research breakthroughs
        - Industry trends and developments
        
        Return ONLY the numbers of the top {top_n} articles in order of importance (1 being most important):
        
        {summaries_text}
        
        Top {top_n} article numbers (comma-separated):
        """
        
        try:
            # Create client with organization header if available
            client_kwargs = {}
            if OPENAI_ORGANIZATION_ID:
                client_kwargs['organization'] = OPENAI_ORGANIZATION_ID
                
            client = openai.OpenAI(**client_kwargs)
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Much cheaper model
                messages=[
                    {"role": "system", "content": "You are an expert AI analyst. Select the most important AI news stories based on technical significance, business impact, and research value."},
                    {"role": "user", "content": ranking_prompt}
                ],
                max_tokens=50,  # Reduced tokens for ranking
                temperature=0.2
            )
            
            # Parse the response to get article indices
            response_text = response.choices[0].message.content.strip()
            try:
                # Extract numbers from response
                import re
                numbers = re.findall(r'\d+', response_text)
                top_indices = [int(num) - 1 for num in numbers[:top_n]]  # Convert to 0-based indexing
                
                # Get the top articles
                top_articles = [self.summarized_articles[i] for i in top_indices if i < len(self.summarized_articles)]
                
                self.top_articles = top_articles
                logger.info(f"Selected top {len(self.top_articles)} articles")
                return self.top_articles
                
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing ranking response: {e}")
                # Fallback: return first N articles
                self.top_articles = self.summarized_articles[:top_n]
                return self.top_articles
                
        except Exception as e:
            logger.error(f"Error ranking articles: {e}")
            # Fallback: return first N articles
            self.top_articles = self.summarized_articles[:top_n]
            return self.top_articles
    
    def output_results(self, date: Optional[str] = None, output_format: str = 'markdown') -> str:
        """
        Output the results in the specified format.
        
        Args:
            date: Date string for filename
            output_format: Output format ('markdown', 'notion', 'email')
            
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
            return content
        else:
            logger.error("Failed to post to Notion")
            return ""
    
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
    
    def _generate_markdown_content(self, date: str) -> str:
        """Generate markdown content for output."""
        content = f"# Top AI News - {date}\n\n"
        content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "## Top 10 AI Updates of the Day\n\n"
        
        for i, article in enumerate(self.top_articles, 1):
            content += f"### {i}. {article.title}\n\n"
            content += f"**Source:** {article.source}\n\n"
            content += f"**Summary:** {article.summary}\n\n"
            content += f"**Link:** {article.url}\n\n"
            content += "---\n\n"
        
        return content
    
    def run_daily_pipeline(self, date: Optional[str] = None, output_format: str = 'markdown') -> str:
        """
        Run the complete daily pipeline.
        
        Args:
            date: Optional date string
            output_format: Output format
            
        Returns:
            Output content
        """
        logger.info("Starting daily AI news pipeline...")
        
        # Step 1: Get articles
        self.get_articles(date)
        
        # Step 2: Summarize articles
        self.summarize_articles()
        
        # Step 3: Rank top articles
        self.rank_top_articles()
        
        # Step 4: Output results
        output = self.output_results(date, output_format)
        
        logger.info("Daily pipeline completed successfully")
        return output


def main():
    """Main entry point for the AI News Agent."""
    parser = argparse.ArgumentParser(description='AI News Agent - Daily AI News Aggregator')
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--output', choices=['markdown', 'notion', 'email'], default='markdown', 
                       help='Output format (default: markdown)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--schedule', action='store_true', help='Run scheduled daily')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    agent = AINewsAgent()
    
    if args.schedule:
        logger.info("Starting scheduled daily runs...")
        schedule.every().day.at("09:00").do(agent.run_daily_pipeline)
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Run once
        output = agent.run_daily_pipeline(args.date, args.output)
        print(f"\n{output}")


if __name__ == "__main__":
    main() 