#!/usr/bin/env python3
"""
Daily AI News Runner (LaunchAgent)

This script is intended to be triggered by macOS LaunchAgent (or cron) at 9:00 AM and sends results to Notion (and optionally to Slack).
It runs once, posts results, sends notifications, then exits.
It also includes cost monitoring and iOS notification support.
"""

import os
import sys
import time
# import schedule
import logging
from datetime import datetime
from ai_news_agent import AINewsAgent
from utils import SlackClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def send_ios_notification(title: str, message: str, url: str = None):
    """Send notification to iOS using multiple methods."""
    # Method 1: Try Pushover (iPhone notifications)
    try:
        from pushover_complete import PushoverAPI
        pushover_token = os.getenv('PUSHOVER_TOKEN')
        pushover_user = os.getenv('PUSHOVER_USER') or os.getenv('PUSHOVER_USER_KEY')
        
        if pushover_token and pushover_user:
            pushover = PushoverAPI(pushover_token)
            
            # Add URL to message if provided
            if url:
                message += f"\n\n🔗 {url}"
            
            pushover.send_message(
                pushover_user,
                message,
                title=title,
                priority=1,
                url=url if url else None
            )
            logger.info("📱 iPhone notification sent via Pushover")
            return
    except ImportError:
        logger.warning("Pushover not installed. Install with: pip install pushover-complete")
    except Exception as e:
        logger.warning(f"Pushover notification failed: {e}")
    
    # Method 2: Fallback to terminal-notifier (Mac only)
    try:
        import subprocess
        subprocess.run([
            'terminal-notifier',
            '-title', title,
            '-message', message,
            '-sound', 'default'
        ], check=False)
        logger.info("💻 Mac notification sent via terminal-notifier")
    except Exception as e:
        logger.warning(f"Could not send Mac notification: {e}")

def run_daily_ai_news():
    """Run the daily AI news pipeline."""
    try:
        logger.info("🚀 Starting daily AI news pipeline...")
        
        # Track start time for cost monitoring
        start_time = time.time()
        
        # Initialize agent
        agent = AINewsAgent()
        
        # Run the pipeline and output to Notion
        today = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%I:%M %p')
        day_name = datetime.now().strftime('%A')
        
        def _article_date_filter_enabled() -> bool:
            return os.getenv("ARTICLE_DATE_FILTER", "").strip().lower() in ("1", "true", "yes", "on")

        output = agent.run_daily_pipeline(
            today,
            'notion',
            filter_by_date=_article_date_filter_enabled(),
        )

        # Also post the same content to Slack
        slack = SlackClient()

        MAX_LEN = 35000
        slack_text = output
        if slack_text and len(slack_text) > MAX_LEN:
            slack_text = slack_text[:MAX_LEN] + "\n\n...(truncated)"

        slack_ok = slack.send_message(slack_text)

        if not slack_ok:
            logger.warning("❌ Slack post failed")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        logger.info(f"✅ Daily pipeline completed in {execution_time:.2f} seconds")
        
        # Create rich notification with headlines
        if hasattr(agent, 'top_articles') and agent.top_articles:
            # Get headlines (first 3 for notification)
            headlines = []
            for i, article in enumerate(agent.top_articles[:3], 1):
                headline = article.title[:50] + "..." if len(article.title) > 50 else article.title
                headlines.append(f"{i}. {headline}")
            
            # Create notification message
            notification_message = f"📅 {day_name}, {today} at {current_time}\n\n"
            notification_message += "🔥 Top AI News Headlines:\n"
            notification_message += "\n".join(headlines)
            notification_message += f"\n\n📊 Total: {len(agent.top_articles)} articles"
            
            # Get Notion page URL if available
            notion_url = getattr(agent, 'last_notion_url', None)
            if notion_url:
                notification_message += f"\n\n📱 Tap to view in Notion"
            
            # Send rich iOS notification
            send_ios_notification(
                f"AI News Agent ✅ - {day_name}",
                notification_message,
                url=notion_url
            )
        else:
            # Fallback notification
            send_ios_notification(
                "AI News Agent ✅",
                f"Daily AI news summary posted to Notion! ({len(agent.top_articles) if hasattr(agent, 'top_articles') else 0} articles)"
            )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in daily pipeline: {e}")
        
        # Send error notification
        send_ios_notification(
            "AI News Agent ❌",
            f"Error: {str(e)[:50]}..."
        )
        
        return False

def run_scheduler():
    """Run the scheduler."""
    logger.info("🕘 Starting AI News Agent runner...")
    logger.info("📅 Running daily news pipeline once, then exiting. Triggered externally (LaunchAgent/cron).")
    
    # Also allow manual testing
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        logger.info("🧪 Running test execution...")
        run_daily_ai_news()
        return
    
    # When run by LaunchAgent, just execute once
    logger.info("🚀 LaunchAgent execution - running daily news pipeline")
    run_daily_ai_news()

if __name__ == "__main__":
    run_scheduler()