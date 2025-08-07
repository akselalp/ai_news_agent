#!/usr/bin/env python3
"""
Test RSS feed URLs for Google Research and DeepMind.
"""

import requests
import feedparser
from urllib.parse import urljoin

def test_rss_feed(url, name):
    """Test an RSS feed URL."""
    print(f"🔍 Testing {name}: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"✅ HTTP Status: {response.status_code}")
        
        # Parse the feed
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
            print(f"⚠️  Feed parsing warning: {feed.bozo_exception}")
        
        print(f"✅ Feed title: {feed.feed.get('title', 'No title')}")
        print(f"✅ Number of entries: {len(feed.entries)}")
        
        if feed.entries:
            print(f"✅ Latest entry: {feed.entries[0].get('title', 'No title')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test the RSS feeds."""
    print("🧪 Testing RSS Feed URLs\n")
    
    # Test multiple possible URLs
    feeds = [
        ("https://research.google/blog/feed.xml", "Google Research (feed.xml)"),
        ("https://research.google/blog/feed/", "Google Research (feed/)"),
        ("https://research.google/blog/rss.xml", "Google Research (rss.xml)"),
        ("https://research.google/blog/", "Google Research (main page)"),
        ("https://deepmind.google/discover/blog/feed.xml", "DeepMind (feed.xml)"),
        ("https://deepmind.google/discover/blog/rss.xml", "DeepMind (rss.xml)"),
        ("https://deepmind.google/discover/blog/", "DeepMind (main page)"),
    ]
    
    results = []
    for url, name in feeds:
        print(f"{'='*50}")
        success = test_rss_feed(url, name)
        results.append((name, success))
        print()
    
    # Summary
    print("📊 Results Summary:")
    for name, success in results:
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"  {name}: {status}")

if __name__ == "__main__":
    main()
