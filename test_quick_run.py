#!/usr/bin/env python3
"""
Quick test to verify the system works after removing broken RSS feeds.
"""

from ai_news_agent import AINewsAgent

def test_quick_run():
    """Test a quick run of the article collection."""
    print("🧪 Testing article collection after removing broken RSS feeds...")
    
    agent = AINewsAgent()
    
    # Test article collection
    articles = agent.get_articles()
    
    print(f"✅ Collected {len(articles)} articles")
    
    # Show sources that worked
    sources = set(article.source for article in articles)
    print(f"✅ Working sources: {', '.join(sources)}")
    
    if articles:
        print(f"✅ Sample article: {articles[0].title[:50]}...")
    
    return len(articles) > 0

if __name__ == "__main__":
    success = test_quick_run()
    if success:
        print("\n🎉 System is working correctly!")
    else:
        print("\n💥 System has issues.")
