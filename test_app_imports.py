#!/usr/bin/env python
"""
Simple test to verify app imports work correctly.
Run this to check for import errors before running the full Streamlit app.
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports for cat_fetches app...")

    try:
        # Test that the services can be imported
        from services.news_service import NewsService, validate_topic
        print("✅ news_service imports successful")

        from services.logging_service import logger, log_info, ErrorIds
        print("✅ logging_service imports successful")

        from config import settings
        print("✅ config imports successful")

        print("\n🎉 All imports successful! The app should run without import errors.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file with all required environment variables")
        print("2. Installed all dependencies: pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"❌ Other error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)