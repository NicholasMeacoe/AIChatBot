#!/usr/bin/env python3
"""
Test script to verify the enhanced file upload and multimodal functionality
"""

import requests
import json
import os
from PIL import Image
import io
import base64

def test_upload_endpoint():
    """Test the file upload endpoint"""
    print("🧪 Testing file upload endpoint...")
    
    # Create a test image
    img = Image.new('RGB', (100, 100), color='red')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    img_buffer.seek(0)
    
    # Create test files
    files = {
        'files': [
            ('test_image.jpg', img_buffer, 'image/jpeg'),
            ('test_text.txt', io.StringIO('This is a test text file'), 'text/plain')
        ]
    }
    
    try:
        response = requests.post('http://localhost:5000/api/context/upload', files=files)
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Upload test failed: {e}")
        return False

def test_check_images_endpoint():
    """Test the check images endpoint"""
    print("🧪 Testing check images endpoint...")
    
    test_data = {
        'context_items': ['test_image.jpg', 'test_text.txt', 'document.pdf']
    }
    
    try:
        response = requests.post('http://localhost:5000/api/context/check_images', 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Check images response status: {response.status_code}")
        print(f"Check images response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Check images test failed: {e}")
        return False

def test_multimodal_chat():
    """Test the multimodal chat endpoint"""
    print("🧪 Testing multimodal chat endpoint...")
    
    test_data = {
        'message': 'What do you see in this image?',
        'active_context': ['test_image.jpg'],
        'model_name': 'gemini-1.5-pro'
    }
    
    try:
        response = requests.post('http://localhost:5000/api/chat_multimodal',
                               json=test_data,
                               headers={'Content-Type': 'application/json'},
                               stream=True)
        print(f"Multimodal chat response status: {response.status_code}")
        
        # Read streaming response
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if 'text' in data:
                            print(f"Response chunk: {data['text'][:50]}...")
                        elif 'error' in data:
                            print(f"Error: {data['error']}")
                    except json.JSONDecodeError:
                        pass
        
        return response.status_code == 200
    except Exception as e:
        print(f"Multimodal chat test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting enhanced file upload and multimodal tests...")
    
    tests = [
        ("File Upload", test_upload_endpoint),
        ("Check Images", test_check_images_endpoint),
        ("Multimodal Chat", test_multimodal_chat)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name} test: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name} test: FAILED with exception: {e}")
            results.append((test_name, False))
    
    print(f"\n{'='*50}")
    print("📊 Test Summary:")
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
