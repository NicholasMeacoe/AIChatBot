#!/usr/bin/env python3
"""
Simple test script to verify the upload endpoint is working
"""

import requests
import io
import os

def test_upload():
    """Test the upload endpoint"""
    print("🧪 Testing upload endpoint...")
    
    # Create a simple text file content
    test_content = "Hello, this is a test file!"
    
    try:
        # Create files dictionary for requests
        files = {
            'files': ('test.txt', test_content, 'text/plain')
        }
        
        # Test the endpoint
        response = requests.post('http://localhost:5000/api/context/upload', files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"Uploaded files: {data.get('uploaded_files', [])}")
            return True
        else:
            print("❌ Upload failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_check_images():
    """Test the check images endpoint"""
    print("\n🧪 Testing check images endpoint...")
    
    test_data = {
        'context_items': ['test.jpg', 'document.txt', 'image.png']
    }
    
    try:
        response = requests.post('http://localhost:5000/api/context/check_images', 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Check images endpoint working!")
            return True
        else:
            print("❌ Check images failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing AIChatBot upload functionality...")
    print("Make sure to start the Flask app first with: python app.py")
    print("=" * 50)
    
    upload_ok = test_upload()
    images_ok = test_check_images()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Upload endpoint: {'✅ PASS' if upload_ok else '❌ FAIL'}")
    print(f"Check images endpoint: {'✅ PASS' if images_ok else '❌ FAIL'}")
    
    if upload_ok and images_ok:
        print("\n🎉 All tests passed! Upload functionality is working.")
    else:
        print("\n⚠️ Some tests failed. Check the server logs for details.")
