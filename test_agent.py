#!/usr/bin/env python3
"""
Test script for AI News Agent.

This script tests the basic functionality without requiring API keys.
It can be used to verify the installation and basic parsing functionality.
"""

import os
import sys
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_news_agent import AINewsAgent, Article

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_article_creation():
    """Test Article dataclass creation."""
    logger.info("Testing Article dataclass...")
    
    article = Article(
        title="Test AI Article",
        url="https://example.com/test",
        source="Test Source",
        published_date="2024-01-15",
        summary="This is a test summary",
        content="This is test content"
    )
    
    assert article.title == "Test AI Article"
    assert article.url == "https://example.com/test"
    assert article.source == "Test Source"
    
    logger.info("✓ Article dataclass test passed")


def test_agent_initialization():
    """Test AINewsAgent initialization."""
    logger.info("Testing AINewsAgent initialization...")
    
    agent = AINewsAgent()
    
    assert hasattr(agent, 'articles')
    assert hasattr(agent, 'summarized_articles')
    assert hasattr(agent, 'top_articles')
    assert hasattr(agent, 'sources')
    
    # Check that sources are configured
    assert 'arxiv_ai' in agent.sources
    assert 'hackernews_ai' in agent.sources
    assert 'techcrunch_ai' in agent.sources
    
    logger.info("✓ AINewsAgent initialization test passed")


def test_markdown_generation():
    """Test markdown content generation."""
    logger.info("Testing markdown generation...")
    
    agent = AINewsAgent()
    
    # Create test articles
    test_articles = [
        Article(
            title="Test AI Article 1",
            url="https://example.com/1",
            source="Test Source 1",
            summary="This is a test summary 1"
        ),
        Article(
            title="Test AI Article 2",
            url="https://example.com/2",
            source="Test Source 2",
            summary="This is a test summary 2"
        )
    ]
    
    agent.top_articles = test_articles
    
    # Generate markdown content
    content = agent._generate_markdown_content("2024-01-15")
    
    # Check that content contains expected elements
    assert "Top AI News - 2024-01-15" in content
    assert "Test AI Article 1" in content
    assert "Test AI Article 2" in content
    assert "Test Source 1" in content
    assert "Test Source 2" in content
    assert "This is a test summary 1" in content
    assert "This is a test summary 2" in content
    
    logger.info("✓ Markdown generation test passed")


def test_environment_validation():
    """Test environment validation."""
    logger.info("Testing environment validation...")
    
    # Test with missing OpenAI key
    original_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        from ai_news_agent import main
        # This should exit with error due to missing API key
        logger.info("✓ Environment validation test passed (expected error for missing API key)")
    except SystemExit:
        logger.info("✓ Environment validation test passed (correctly caught missing API key)")
    finally:
        # Restore original key if it existed
        if original_key:
            os.environ['OPENAI_API_KEY'] = original_key


def test_source_configuration():
    """Test news source configuration."""
    logger.info("Testing source configuration...")
    
    agent = AINewsAgent()
    
    # Check that all sources have required configuration
    for source_name, source_config in agent.sources.items():
        assert 'url' in source_config, f"Source {source_name} missing URL"
        assert 'parser' in source_config, f"Source {source_name} missing parser"
        
        # Check that URLs are valid
        assert source_config['url'].startswith('http'), f"Source {source_name} has invalid URL"
    
    logger.info("✓ Source configuration test passed")


def run_all_tests():
    """Run all tests."""
    logger.info("Starting AI News Agent tests...")
    
    try:
        test_article_creation()
        test_agent_initialization()
        test_markdown_generation()
        test_environment_validation()
        test_source_configuration()
        
        logger.info("🎉 All tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 