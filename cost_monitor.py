#!/usr/bin/env python3
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
        print("🎯 Target: Keep daily costs under $0.02 with optimized settings")
        
    except Exception as e:
        print(f"Error checking usage: {e}")

if __name__ == "__main__":
    check_usage()
