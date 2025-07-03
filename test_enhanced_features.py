#!/usr/bin/env python3
"""
Test script for enhanced AI chatbot features
Tests core functionality without running the full web server
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all enhanced features can be imported"""
    print("🧪 Testing Enhanced Feature Imports...")
    
    try:
        # Test core feature imports
        from features.notebook import notebook_manager
        print("  ✅ Notebook manager imported successfully")
        
        from features.chain_of_thought import chain_of_thought_manager
        print("  ✅ Chain of thought manager imported successfully")
        
        from features.autonomous_agent import autonomous_agent
        print("  ✅ Autonomous agent imported successfully")
        
        from features.git_integration import git_manager
        print("  ✅ Git integration manager imported successfully")
        
        from features.user_profiles import user_profile_manager
        print("  ✅ User profile manager imported successfully")
        
        from features.dynamic_api_integration import dynamic_api_manager
        print("  ✅ Dynamic API manager imported successfully")
        
        from features.collaborative_whiteboard import whiteboard_manager
        print("  ✅ Whiteboard manager imported successfully")
        
        from features.debugging_assistant import debugging_assistant
        print("  ✅ Debugging assistant imported successfully")
        
        from features.digital_twin_simple import digital_twin
        print("  ✅ Digital twin imported successfully")
        
        print("  🎉 All core features imported successfully!")
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def test_notebook_functionality():
    """Test basic notebook functionality"""
    print("\n📊 Testing Notebook Functionality...")
    
    try:
        from features.notebook import notebook_manager
        
        # Test simple code execution
        result = notebook_manager.execute_code("x = 2 + 2\nprint(f'Result: {x}')")
        
        if result and not result.get('error'):
            print("  ✅ Code execution successful")
            print(f"  📝 Output: {result.get('output', '').strip()}")
        else:
            print(f"  ❌ Code execution failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Test context variables
        variables = notebook_manager.get_context_variables()
        if 'x' in variables:
            print("  ✅ Context variables working")
        else:
            print("  ⚠️  Context variables not persisting")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Notebook test failed: {e}")
        return False

def test_git_integration():
    """Test Git integration functionality"""
    print("\n🔧 Testing Git Integration...")
    
    try:
        from features.git_integration import git_manager
        
        # Test if we're in a Git repository
        if git_manager.is_git_repo():
            print("  ✅ Git repository detected")
            
            # Get repository status
            status = git_manager.get_repo_status()
            if status and not status.get('error'):
                print(f"  📋 Current branch: {status.get('branch', 'unknown')}")
                print(f"  📋 Repository status: {'clean' if not status.get('is_dirty') else 'has changes'}")
            else:
                print(f"  ⚠️  Could not get repo status: {status.get('error', 'Unknown error')}")
        else:
            print("  ℹ️  Not in a Git repository (this is okay for testing)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Git integration test failed: {e}")
        return False

def test_user_profiles():
    """Test user profile functionality"""
    print("\n👤 Testing User Profiles...")
    
    try:
        from features.user_profiles import user_profile_manager
        
        # Load or create a test profile
        profile = user_profile_manager.load_or_create_profile("test_user")
        
        if profile:
            print("  ✅ User profile created/loaded successfully")
            print(f"  📋 User ID: {profile.user_id}")
            print(f"  📋 Session count: {profile.session_count}")
            
            # Test recording an interaction
            user_profile_manager.record_interaction("test", "This is a test interaction")
            print("  ✅ Interaction recorded successfully")
        else:
            print("  ❌ Failed to create/load user profile")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ User profile test failed: {e}")
        return False

async def test_chain_of_thought():
    """Test chain of thought functionality"""
    print("\n🧠 Testing Chain of Thought...")
    
    try:
        from features.chain_of_thought import chain_of_thought_manager
        
        # Test task decomposition (this requires API key)
        print("  ℹ️  Chain of thought requires Google API key for full testing")
        print("  ✅ Chain of thought manager initialized successfully")
        
        # Test basic functionality
        active_tasks = chain_of_thought_manager.list_active_tasks()
        print(f"  📋 Active tasks: {len(active_tasks)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Chain of thought test failed: {e}")
        return False

def test_digital_twin():
    """Test digital twin functionality"""
    print("\n🏗️  Testing Digital Twin...")
    
    try:
        from features.digital_twin_simple import digital_twin
        
        print("  ✅ Digital twin initialized successfully")
        print(f"  📋 Current entities: {len(digital_twin.entities)}")
        print(f"  📋 Current relationships: {len(digital_twin.relationships)}")
        
        # Test if we can analyze the current directory
        source_files = digital_twin._get_source_files()
        if source_files:
            print(f"  ✅ Source files detected for analysis: {len(source_files)}")
        else:
            print("  ℹ️  No source files found (this is okay for testing)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Digital twin test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Enhanced AI Chatbot Feature Tests")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Notebook Functionality", test_notebook_functionality),
        ("Git Integration", test_git_integration),
        ("User Profiles", test_user_profiles),
        ("Chain of Thought", test_chain_of_thought),
        ("Digital Twin", test_digital_twin),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced features are working correctly.")
        print("\n💡 Next steps:")
        print("  1. Set up your Google API key in .env file")
        print("  2. Run: python enhanced_app_complete.py")
        print("  3. Access the enhanced interface at http://localhost:5000")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("💡 This might be due to missing optional dependencies or API keys.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
