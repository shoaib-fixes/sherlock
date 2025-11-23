#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test script to verify Reddit API authentication works.
"""

import os
from dotenv import load_dotenv
from reddit_auth import RedditAuthenticator, AuthenticationError, RateLimitError

# Load environment variables
load_dotenv()

def test_authentication():
    """Test the Reddit authentication."""
    print("Testing Reddit API authentication...")

    try:
        # Create authenticator
        auth = RedditAuthenticator()
        print("[OK] Authenticator created successfully")

        # Test authentication
        token = auth.authenticate()
        print("[OK] Authentication successful")

        # Test a simple API call
        headers = auth.get_headers()
        print("[OK] Headers generated successfully")

        # Test a simple request (user about endpoint for a known user)
        result = auth.make_request('/user/spez/about')
        print("[OK] API request successful")

        if 'data' in result and 'name' in result['data']:
            print(f"[OK] User data retrieved: {result['data']['name']}")
        else:
            print("[OK] API response received (but user data structure may differ)")

        print("\n[SUCCESS] All authentication tests passed!")

    except AuthenticationError as e:
        print(f"[ERROR] Authentication failed: {e}")
        return False
    except RateLimitError as e:
        print(f"[ERROR] Rate limit exceeded: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

    return True

if __name__ == "__main__":
    # Check if environment variables are set to non-placeholder values
    client_id = os.environ.get('REDDIT_CLIENT_ID')
    client_secret = os.environ.get('REDDIT_SECRET')

    if not client_id or not client_secret or client_id == 'your_reddit_client_id_here' or client_secret == 'your_reddit_secret_here':
        print("[ERROR] Valid Reddit API credentials not set. Please update your .env file with real credentials.")
        print("   Get credentials from: https://www.reddit.com/prefs/apps")
        print("   Current values:")
        print(f"   REDDIT_CLIENT_ID: {client_id}")
        print(f"   REDDIT_SECRET: {client_secret}")
        exit(1)

    print("[OK] Environment variables loaded successfully")
    success = test_authentication()
    exit(0 if success else 1)
