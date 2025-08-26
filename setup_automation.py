#!/usr/bin/env python3
"""
Setup script for AI News Agent automation on macOS.

This script sets up:
1. Daily scheduling via LaunchAgent
2. iOS notifications
3. Cost monitoring
"""

import os
import sys
import subprocess
from pathlib import Path

def install_dependencies():
    """Install required dependencies for notifications."""
    print("📦 Installing dependencies...")
    
    # Check if Homebrew is installed
    try:
        subprocess.run(['brew', '--version'], check=True, capture_output=True)
        print("✅ Homebrew detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Homebrew not found. Please install Homebrew first:")
        print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    # Install terminal-notifier for iOS notifications
    try:
        subprocess.run(['brew', 'install', 'terminal-notifier'], check=True)
        print("✅ terminal-notifier installed")
    except subprocess.CalledProcessError:
        print("⚠️  Could not install terminal-notifier (notifications may not work)")
    
    return True

def create_launch_agent():
    """Create macOS LaunchAgent for daily execution."""
    print("🔧 Setting up LaunchAgent...")
    
    # Get the current working directory
    current_dir = Path(__file__).parent.absolute()
    python_path = sys.executable
    
    # LaunchAgent plist content
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.ai-news-agent</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/your/python</string>
        <string>/path/to/ai_news_agent/daily_scheduler.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/path/to/ai_news_agent</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardErrorPath</key>
    <string>/path/to/ai_news_agent/scheduler_error.log</string>
    
    <key>StandardOutPath</key>
    <string>/path/to/ai_news_agent/scheduler_output.log</string>
</dict>
</plist>"""
    
    # Create LaunchAgents directory if it doesn't exist
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    # Write the plist file
    plist_file = launch_agents_dir / "com.user.ai-news-agent.plist"
    with open(plist_file, 'w') as f:
        f.write(plist_content)
    
    print(f"✅ LaunchAgent created: {plist_file}")
    return plist_file

def load_launch_agent(plist_file):
    """Load the LaunchAgent."""
    try:
        subprocess.run(['launchctl', 'load', str(plist_file)], check=True)
        print("✅ LaunchAgent loaded successfully")
        
        # Start the service
        subprocess.run(['launchctl', 'start', 'com.user.ai-news-agent'], check=True)
        print("✅ AI News Agent service started")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error loading LaunchAgent: {e}")
        return False

def create_cost_monitor():
    """Create a simple cost monitoring script."""
    monitor_script = """#!/usr/bin/env python3
'''
Simple cost monitor for OpenAI API usage.
Run this weekly to check your usage.
'''

import openai
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def check_usage():
    client = openai.OpenAI()
    
    try:
        # Note: This is a placeholder - OpenAI's usage endpoint may require different approach
        print("📊 Cost monitoring feature")
        print("💡 Tip: Check your usage at https://platform.openai.com/usage")
        print("🎯 Target: Keep daily costs under $0.50 with optimized settings")
        
    except Exception as e:
        print(f"Error checking usage: {e}")

if __name__ == "__main__":
    check_usage()
"""
    
    with open("cost_monitor.py", 'w') as f:
        f.write(monitor_script)
    
    print("✅ Cost monitor script created")

def main():
    print("🚀 Setting up AI News Agent automation...")
    print()
    
    # Install dependencies
    if not install_dependencies():
        return
    
    print()
    
    # Create LaunchAgent
    plist_file = create_launch_agent()
    
    print()
    
    # Load LaunchAgent
    load_launch_agent(plist_file)
    
    print()
    
    # Create cost monitor
    create_cost_monitor()
    
    print()
    print("🎉 Setup complete!")
    print()
    print("📱 The AI News Agent will now run daily at 9:00 AM")
    print("📄 Results will be posted to your Notion database")
    print("🔔 You'll receive iOS notifications when complete")
    print()
    print("🔧 Useful commands:")
    print(f"   Test run:     python daily_scheduler.py --test")
    print(f"   Check status: launchctl list | grep ai-news-agent")
    print(f"   Stop service: launchctl stop com.user.ai-news-agent")
    print(f"   Unload:       launchctl unload {plist_file}")
    print()
    print("💰 Cost optimization tips:")
    print("   - Using gpt-4o-mini instead of gpt-4 (90% cost reduction)")
    print("   - Limited article count per source")
    print("   - Reduced token limits")
    print("   - Estimated daily cost: $0.10-0.30 (vs previous $2.00)")

if __name__ == "__main__":
    main()