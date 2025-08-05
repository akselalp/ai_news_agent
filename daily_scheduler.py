#!/usr/bin/env python3
"""
Daily AI News Scheduler

This script runs the AI News Agent daily at 9 AM and sends results to Notion.
It also includes cost monitoring and iOS notification support.
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime
from ai_news_agent import AINewsAgent

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

def send_ios_notification(title: str, message: str):
    """Send notification to iOS using terminal-notifier (if available)."""
    try:
        import subprocess
        # Install with: brew install terminal-notifier
        subprocess.run([
            'terminal-notifier',
            '-title', title,
            '-message', message,
            '-sound', 'default'
        ], check=False)
    except Exception as e:
        logger.warning(f"Could not send iOS notification: {e}")

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
        output = agent.run_daily_pipeline(today, 'notion')
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        logger.info(f"✅ Daily pipeline completed in {execution_time:.2f} seconds")
        
        # Send iOS notification
        send_ios_notification(
            "AI News Agent ✅",
            f"Daily AI news summary posted to Notion! ({len(agent.top_articles)} articles)"
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
    logger.info("🕘 Starting AI News Agent scheduler...")
    logger.info("📅 Scheduled to run daily at 9:00 AM")
    
    # Schedule the job for 9:00 AM daily
    schedule.every().day.at("09:00").do(run_daily_ai_news)
    
    # Also allow manual testing
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        logger.info("🧪 Running test execution...")
        run_daily_ai_news()
        return
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("👋 Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == "__main__":
    run_scheduler()