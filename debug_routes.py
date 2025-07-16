#!/usr/bin/env python3
"""
Debug script to check what routes are registered in the Flask app
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the Flask app
    from app import app
    
    print("Flask app imported successfully!")
    print("\nRegistered routes:")
    print("-" * 50)
    
    # List all registered routes
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"{rule.rule:<30} {methods:<15} {rule.endpoint}")
    
    print(f"\nTotal routes: {len(list(app.url_map.iter_rules()))}")
    
    # Test if specific routes exist
    test_routes = ['/test-submission', '/simple', '/minimal', '/clean', '/test-route']
    
    print("\nTesting specific routes:")
    print("-" * 30)
    
    with app.test_client() as client:
        for route in test_routes:
            try:
                response = client.get(route)
                status = "✓" if response.status_code == 200 else f"✗ ({response.status_code})"
                print(f"{route:<20} {status}")
            except Exception as e:
                print(f"{route:<20} ✗ (Error: {e})")

except ImportError as e:
    print(f"Error importing Flask app: {e}")
    print("Make sure you're in the correct directory and all dependencies are installed.")
except Exception as e:
    print(f"Unexpected error: {e}")
