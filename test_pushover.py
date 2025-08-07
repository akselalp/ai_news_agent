#!/usr/bin/env python3
"""
Test Pushover notification functionality.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_pushover_config():
    """Test Pushover configuration."""
    print("🔍 Testing Pushover configuration...")
    
    pushover_token = os.getenv('PUSHOVER_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER')
    
    if not pushover_token:
        print("❌ PUSHOVER_TOKEN not found in environment variables")
        return False
    
    if not pushover_user:
        print("❌ PUSHOVER_USER not found in environment variables")
        return False
    
    print(f"✅ Pushover Token found: {pushover_token[:10]}...")
    print(f"✅ Pushover User found: {pushover_user[:10]}...")
    
    try:
        from pushover_complete import PushoverAPI
        pushover = PushoverAPI(pushover_token)
        
        # Send a test notification
        response = pushover.send_message(
            pushover_user,
            "🧪 Test notification from AI News Agent",
            title="AI News Agent Test",
            priority=0  # Normal priority for testing
        )
        
        print("✅ Pushover test notification sent successfully!")
        print(f"📱 Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Pushover test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_pushover_config()
    if success:
        print("\n🎉 Pushover notifications are working!")
    else:
        print("\n💥 Pushover notifications are not configured properly.")
        print("Please check your .env file for PUSHOVER_TOKEN and PUSHOVER_USER")
