#!/usr/bin/env python3
"""
Wrapper script to ensure .env file is loaded before running the AI News Agent.
This is needed for LaunchAgent to properly load environment variables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Load environment and run the daily scheduler."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Load the .env file explicitly
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded .env file from: {env_file}")
        
        # Verify API key is loaded
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"✅ API Key loaded: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("❌ No API key found in .env file")
            return 1
    else:
        print(f"❌ .env file not found at: {env_file}")
        return 1
    
    # Import and run the daily scheduler
    try:
        from daily_scheduler import run_daily_ai_news
        run_daily_ai_news()
        return 0
    except Exception as e:
        print(f"❌ Error running daily scheduler: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
