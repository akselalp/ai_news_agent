#!/usr/bin/env python3
"""
Setup script for AI News Agent.

This script helps with initial setup and configuration.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)


def setup_environment():
    """Set up environment file."""
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if env_file.exists():
        print("✓ .env file already exists")
        return
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✓ Created .env file from template")
        print("⚠️  Please edit .env file with your API keys")
    else:
        print("❌ env_example.txt not found")
        sys.exit(1)


def validate_setup():
    """Validate the setup."""
    print("Validating setup...")
    
    # Check if .env exists
    if not Path(".env").exists():
        print("❌ .env file not found. Please run setup again.")
        return False
    
    # Check if requirements are installed
    try:
        import requests
        import feedparser
        import openai
        print("✓ Required packages are installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        return False
    
    print("✓ Setup validation passed")
    return True


def run_tests():
    """Run basic tests."""
    print("Running tests...")
    
    try:
        subprocess.check_call([sys.executable, "test_agent.py"])
        print("✓ Tests passed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Tests failed")
        return False


def main():
    """Main setup function."""
    print("🚀 AI News Agent Setup")
    print("=" * 40)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Setup environment
    setup_environment()
    
    # Validate setup
    if not validate_setup():
        print("❌ Setup validation failed")
        sys.exit(1)
    
    # Run tests
    if not run_tests():
        print("❌ Test validation failed")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your OpenAI API key")
    print("2. Run: python ai_news_agent.py")
    print("3. Check the generated markdown file")
    
    print("\nFor more information, see README.md")


if __name__ == "__main__":
    main() 