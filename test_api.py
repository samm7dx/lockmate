#!/usr/bin/env python3
"""Test script for LOCKMATE API."""

import os
import sys
import time
import threading
import requests
import uvicorn
from secret_wards.api.server import app

def test_api():
    # Set secret (32 bytes base64)
    os.environ["RAKSHA_SECRET"] = "/2R4JyyAqfYl1kPwSWX0IkA/jsSdNH6F4TGM3FezXxU="
    
    # Start server in background thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        # Test health endpoint
        print("Testing /api/health...")
        resp = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        
        # Test list runs
        print("\nTesting /api/runs...")
        resp = requests.get(f"{base_url}/api/runs", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        
        print("\n[OK] All API tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] API test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)