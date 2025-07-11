#!/usr/bin/env python3
"""
Comprehensive test suite for Gemini Chat Application
"""

import requests
import json
import time
import threading
import subprocess
import sys
import os
from datetime import datetime

class GeminiChatTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.app_process = None
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append((test_name, success, message))
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
            
    def start_app(self):
        """Start the Flask application"""
        print("🚀 Starting Flask application...")
        try:
            self.app_process = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            time.sleep(3)  # Wait for app to start
            
            # Test if app is responding
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.log_test("App Startup", True, "Flask app started successfully")
                return True
            else:
                self.log_test("App Startup", False, f"App returned status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("App Startup", False, f"Failed to start app: {e}")
            return False
            
    def stop_app(self):
        """Stop the Flask application"""
        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait()
            
    def test_api_conversations_get(self):
        """Test GET /api/conversations"""
        try:
            response = requests.get(f"{self.base_url}/api/conversations", timeout=5)
            if response.status_code == 200:
                conversations = response.json()
                self.log_test("GET /api/conversations", True, f"Found {len(conversations)} conversations")
                return conversations
            else:
                self.log_test("GET /api/conversations", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("GET /api/conversations", False, str(e))
            return []
            
    def test_api_conversations_post(self):
        """Test POST /api/conversations"""
        try:
            response = requests.post(f"{self.base_url}/api/conversations", timeout=5)
            if response.status_code == 200:
                new_conv = response.json()
                self.log_test("POST /api/conversations", True, f"Created: {new_conv['name']}")
                return new_conv
            else:
                self.log_test("POST /api/conversations", False, f"Status: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("POST /api/conversations", False, str(e))
            return None
            
    def test_api_conversation_history(self, conv_id):
        """Test GET /api/conversations/{id}/history"""
        try:
            response = requests.get(f"{self.base_url}/api/conversations/{conv_id}/history", timeout=5)
            if response.status_code == 200:
                history = response.json()
                self.log_test("GET /api/conversations/{id}/history", True, f"Found {len(history)} messages")
                return history
            else:
                self.log_test("GET /api/conversations/{id}/history", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("GET /api/conversations/{id}/history", False, str(e))
            return []
            
    def test_api_context_files(self):
        """Test GET /api/context/files"""
        try:
            response = requests.get(f"{self.base_url}/api/context/files", timeout=5)
            if response.status_code == 200:
                files = response.json()
                self.log_test("GET /api/context/files", True, f"Found {len(files)} files")
                return files
            else:
                self.log_test("GET /api/context/files", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("GET /api/context/files", False, str(e))
            return []
            
    def test_api_context_folders(self):
        """Test GET /api/context/folders"""
        try:
            response = requests.get(f"{self.base_url}/api/context/folders", timeout=5)
            if response.status_code == 200:
                folders = response.json()
                self.log_test("GET /api/context/folders", True, f"Found {len(folders)} folders")
                return folders
            else:
                self.log_test("GET /api/context/folders", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("GET /api/context/folders", False, str(e))
            return []
            
    def test_main_page(self):
        """Test main page loads"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200 and "Gemini Chat" in response.text:
                self.log_test("Main Page Load", True, "Page loaded with correct title")
                return True
            else:
                self.log_test("Main Page Load", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Main Page Load", False, str(e))
            return False
            
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("GEMINI CHAT APPLICATION - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        # Start application
        if not self.start_app():
            print("❌ Cannot start application. Aborting tests.")
            return False
            
        try:
            # Test main page
            self.test_main_page()
            
            # Test API endpoints
            conversations = self.test_api_conversations_get()
            new_conv = self.test_api_conversations_post()
            
            if conversations:
                self.test_api_conversation_history(conversations[0]['id'])
                
            self.test_api_context_files()
            self.test_api_context_folders()
            
        finally:
            # Stop application
            self.stop_app()
            
        # Print results
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
            if message and not success:
                print(f"    Error: {message}")
                
        print(f"\n📊 FINAL SCORE: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Application is fully functional.")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
            
        return passed == total

if __name__ == "__main__":
    tester = GeminiChatTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
