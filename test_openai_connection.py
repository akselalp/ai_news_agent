#!/usr/bin/env python3
"""
Test OpenAI API connection with organization and project headers.
"""

import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection."""
    print("🔍 Testing OpenAI API connection...")
    
    # Get API key and headers
    api_key = os.getenv('OPENAI_API_KEY')
    org_id = os.getenv('OPENAI_ORGANIZATION_ID')
    project_id = os.getenv('OPENAI_PROJECT_ID')
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    if org_id:
        print(f"✅ Organization ID found: {org_id}")
    else:
        print("⚠️  No Organization ID found")
    
    if project_id:
        print(f"✅ Project ID found: {project_id}")
    else:
        print("⚠️  No Project ID found")
    
    try:
        # Create client with organization header
        client_kwargs = {}
        if org_id:
            client_kwargs['organization'] = org_id
            
        client = openai.OpenAI(**client_kwargs)
        
        # Test with a simple completion
        # Note: Project ID might need to be passed differently in older library versions
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello, API test successful!'"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ API test successful! Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_connection()
    if success:
        print("\n🎉 OpenAI API connection is working!")
    else:
        print("\n💥 OpenAI API connection failed. Please check your API key and configuration.")
