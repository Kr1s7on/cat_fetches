#!/usr/bin/env python
"""
Development runner for cat_fetches Streamlit app.
Sets up minimal environment variables for local testing without requiring full config.
"""

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, skip .env loading
    pass

import os
import sys
import subprocess
from pathlib import Path

def setup_dev_environment():
    """Set up development environment variables with safe defaults."""

    # Development defaults - these won't work for actual API calls but allow app to start
    dev_defaults = {
        "GEMINI_API_KEY": "dev_placeholder_gemini_key",
        "NEWS_API_KEY": "dev_placeholder_news_key",
        "SMTP_EMAIL": "dev@example.com",
        "SMTP_PASSWORD": "dev_placeholder_password",
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "APP_ENV": "local"
    }

    print("🔧 Setting up development environment...")

    # Only set if not already present
    for key, value in dev_defaults.items():
        if not os.getenv(key):
            os.environ[key] = value
            print(f"   Set {key}={value}")
        else:
            print(f"   Using existing {key}")

    print("✅ Development environment ready!")
    return True

def run_streamlit():
    """Run the Streamlit app with development settings."""
    try:
        print("\n🚀 Starting Streamlit app...")
        print("   App will be available at: http://localhost:8501")
        print("   Note: News fetching will fail with placeholder API keys")
        print("   Press Ctrl+C to stop\n")

        # Run streamlit
        result = subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0"
        ], check=True)

        return result.returncode == 0

    except KeyboardInterrupt:
        print("\n👋 Stopping development server...")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main development runner."""
    print("🏗️  cat_fetches Development Server")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ app.py not found. Please run from the project root directory.")
        sys.exit(1)

    # Set up development environment
    if not setup_dev_environment():
        sys.exit(1)

    # Test imports first
    print("\n🔍 Testing imports...")
    try:
        from config import settings
        from services.news_service import NewsService
        from services.logging_service import logger
        print("✅ All imports successful!")
    except Exception as e:
        print(f"❌ Import error: {e}")
        print("Make sure you've installed requirements: pip install -r requirements.txt")
        sys.exit(1)

    # Run the app
    success = run_streamlit()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
