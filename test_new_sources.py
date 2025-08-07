#!/usr/bin/env python3
"""
Test the new web scraping sources.
"""

from ai_news_agent import AINewsAgent

def test_new_sources():
    """Test the new web scraping sources."""
    print("🧪 Testing new web scraping sources...")
    
    agent = AINewsAgent()
    
    # Test each new source individually
    new_sources = ['google_research', 'deepmind', 'gemini', 'anthropic', 'mistral_ai', 'qwen', 'asml']
    
    for source_name in new_sources:
        print(f"\n{'='*50}")
        print(f"Testing {source_name}...")
        
        if source_name in agent.sources:
            source_config = agent.sources[source_name]
            try:
                articles = agent._fetch_from_source(source_name, source_config)
                print(f"✅ {source_name}: Found {len(articles)} articles")
                
                if articles:
                    print(f"   Sample: {articles[0].title[:60]}...")
                    print(f"   URL: {articles[0].url}")
                
            except Exception as e:
                print(f"❌ {source_name}: Error - {e}")
        else:
            print(f"⚠️  {source_name}: Not configured")
    
    # Test overall collection
    print(f"\n{'='*50}")
    print("Testing overall article collection...")
    
    all_articles = agent.get_articles()
    print(f"✅ Total articles collected: {len(all_articles)}")
    
    # Show sources that worked
    sources = set(article.source for article in all_articles)
    print(f"✅ Working sources: {', '.join(sorted(sources))}")
    
    return len(all_articles) > 0

if __name__ == "__main__":
    success = test_new_sources()
    if success:
        print("\n🎉 New sources are working!")
    else:
        print("\n💥 Some sources have issues.")
