#!/usr/bin/env python3
"""
Test script to verify authentication and endpoint connectivity.
Run this before deploying to ensure your setup is correct.
"""

import os
from openai import OpenAI

MODEL_NAME = "agents_akash_s_demo-talent-mobility_attrition"
BASE_URL = "https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints"

def test_authentication():
    """Test if we can authenticate and call the endpoint"""
    print("=" * 60)
    print("Testing Databricks Agent Endpoint Authentication")
    print("=" * 60)
    
    # Check for token
    token = os.environ.get('DATABRICKS_TOKEN')
    if not token:
        print("\n❌ DATABRICKS_TOKEN environment variable not set")
        print("\nTo set it, run:")
        print("  export DATABRICKS_TOKEN='your_token_here'")
        print("\nGet your token from:")
        print("  https://docs.databricks.com/en/dev-tools/auth/pat.html")
        return False
    
    print(f"\n✓ Token found (length: {len(token)} characters)")
    
    # Create client
    print(f"\n→ Creating OpenAI client...")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Model: {MODEL_NAME}")
    
    try:
        client = OpenAI(
            api_key=token,
            base_url=BASE_URL
        )
        print("  ✓ Client created")
    except Exception as e:
        print(f"  ❌ Failed to create client: {e}")
        return False
    
    # Test API call
    print("\n→ Testing API call...")
    test_message = "Hello, can you confirm you're working?"
    
    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {
                    "role": "user",
                    "content": test_message
                }
            ]
        )
        
        # Extract response text
        response_text = " ".join(
            getattr(content, "text", "") 
            for output in response.output 
            for content in getattr(output, "content", [])
        )
        
        print("  ✓ API call successful!")
        print(f"\n📝 Response from agent:")
        print("  " + "-" * 56)
        print(f"  {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
        print("  " + "-" * 56)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Your setup is working correctly.")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        print("\nPossible issues:")
        print("  - Token may be invalid or expired")
        print("  - Token may not have access to the serving endpoint")
        print("  - Model name may be incorrect")
        print("  - Endpoint URL may be wrong")
        return False


if __name__ == "__main__":
    success = test_authentication()
    exit(0 if success else 1)

