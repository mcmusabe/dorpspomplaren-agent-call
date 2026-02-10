#!/usr/bin/env python3
"""
Test script voor de order webhook
Test of de webhook server correct werkt en emails verstuurt
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get webhook URL from env or use default
WEBHOOK_URL = os.getenv("RETELL_WEBHOOK_URL") or "http://localhost:8000"

def test_webhook():
    """Test de order webhook met sample data"""
    
    print("=" * 60)
    print("Testing Order Webhook")
    print("=" * 60)
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()
    
    # Sample order data
    test_order = {
        "customer_name": "Test Klant",
        "phone": "0612345678",
        "pickup_time": "18:30",
        "items": [
            {
                "name": "Friet",
                "qty": 2,
                "notes": "met mayonaise"
            },
            {
                "name": "Frikandel",
                "qty": 1,
                "notes": None
            },
            {
                "name": "Hamburger",
                "qty": 1,
                "notes": "zonder ui"
            }
        ],
        "extra_notes": "Graag snel klaar"
    }
    
    print("Sending test order...")
    print(f"Order data: {json.dumps(test_order, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        # Test health endpoint first
        health_url = f"{WEBHOOK_URL}/health"
        print(f"1. Testing health endpoint: {health_url}")
        health_response = requests.get(health_url, timeout=5)
        if health_response.status_code == 200:
            print(f"   ✓ Health check OK: {health_response.json()}")
        else:
            print(f"   ✗ Health check failed: {health_response.status_code}")
            return False
        print()
        
        # Test order endpoint
        order_url = f"{WEBHOOK_URL}/order"
        print(f"2. Testing order endpoint: {order_url}")
        order_response = requests.post(
            order_url,
            json=test_order,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status code: {order_response.status_code}")
        
        if order_response.status_code == 200:
            result = order_response.json()
            print(f"   ✓ Order sent successfully!")
            print(f"   Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            print()
            print("=" * 60)
            print("✅ TEST SUCCESSFUL")
            print("=" * 60)
            print("Check your email inbox for the order confirmation!")
            return True
        else:
            print(f"   ✗ Order failed: {order_response.status_code}")
            print(f"   Response: {order_response.text}")
            print()
            print("=" * 60)
            print("❌ TEST FAILED")
            print("=" * 60)
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ✗ Connection error: Could not connect to webhook server")
        print("   Make sure webhook_order.py is running on port 8000")
        print()
        print("=" * 60)
        print("❌ TEST FAILED - Server not running")
        print("=" * 60)
        print("Start the webhook server with: python3 webhook_order.py")
        return False
    except requests.exceptions.Timeout:
        print("   ✗ Timeout: Server took too long to respond")
        print()
        print("=" * 60)
        print("❌ TEST FAILED - Timeout")
        print("=" * 60)
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print()
        print("=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_webhook()
    exit(0 if success else 1)

