#!/usr/bin/env python3
"""
Test script for enhanced AI chatbot features
Tests core functionality without running the full web server
"""

import sys
import os
import asyncio
import pytest
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
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        pytest.fail(f"Import failed: {e}")

def test_notebook_functionality():
    """Test notebook manager basic functionality"""
    print("🧪 Testing Notebook Functionality...")
    
    try:
        from features.notebook import notebook_manager
        
        # Test code execution
        result = notebook_manager.execute_code("print('Hello from notebook!')")
        assert result is not None
        print("  ✅ Code execution working")
        
        # Test variable storage
        notebook_manager.execute_code("test_var = 42")
        result = notebook_manager.execute_code("print(test_var)")
        assert "42" in result.get('output', '')
        print("  ✅ Variable persistence working")
        
        print("  🎉 Notebook functionality tests passed!")
        
    except Exception as e:
        print(f"  ❌ Notebook test failed: {e}")
        pytest.fail(f"Notebook test failed: {e}")

def test_git_integration():
    """Test git integration functionality"""
    print("🧪 Testing Git Integration...")
    
    try:
        from features.git_integration import git_manager
        
        # Test commit message generation
        message = git_manager.generate_commit_message("Added new feature for user authentication")
        assert message is not None
        assert len(message) > 0
        print("  ✅ Commit message generation working")
        
        # Test status check (should work even without git repo)
        try:
            status = git_manager.get_status()
            print("  ✅ Git status check working")
        except Exception:
            print("  ⚠️  Git status check skipped (no git repo)")
        
        print("  🎉 Git integration tests passed!")
        
    except Exception as e:
        print(f"  ❌ Git integration test failed: {e}")
        pytest.fail(f"Git integration test failed: {e}")

def test_user_profiles():
    """Test user profile management"""
    print("🧪 Testing User Profiles...")
    
    try:
        from features.user_profiles import user_profile_manager
        
        # Test profile creation
        test_user = "test_user_123"
        user_profile_manager.update_interaction(test_user, "test message", "test response")
        print("  ✅ User interaction logging working")
        
        # Test preference learning
        preferences = user_profile_manager.get_user_preferences(test_user)
        assert preferences is not None
        print("  ✅ User preference retrieval working")
        
        print("  🎉 User profile tests passed!")
        
    except Exception as e:
        print(f"  ❌ User profile test failed: {e}")
        pytest.fail(f"User profile test failed: {e}")

@pytest.mark.asyncio
async def test_chain_of_thought():
    """Test chain of thought processing"""
    print("🧪 Testing Chain of Thought...")
    
    try:
        from features.chain_of_thought import chain_of_thought_manager
        
        # Test task decomposition
        task = "Create a simple Python function to calculate fibonacci numbers"
        steps = await chain_of_thought_manager.decompose_task(task)
        assert steps is not None
        assert len(steps) > 0
        print("  ✅ Task decomposition working")
        
        print("  🎉 Chain of thought tests passed!")
        
    except Exception as e:
        print(f"  ❌ Chain of thought test failed: {e}")
        pytest.fail(f"Chain of thought test failed: {e}")

def test_digital_twin():
    """Test digital twin functionality"""
    print("🧪 Testing Digital Twin...")
    
    try:
        from features.digital_twin_simple import digital_twin
        
        # Test codebase analysis
        analysis = digital_twin.analyze_codebase(".")
        assert analysis is not None
        print("  ✅ Codebase analysis working")
        
        # Test file analysis
        if os.path.exists("app.py"):
            file_analysis = digital_twin.analyze_file("app.py")
            assert file_analysis is not None
            print("  ✅ File analysis working")
        
        print("  🎉 Digital twin tests passed!")
        
    except Exception as e:
        print(f"  ❌ Digital twin test failed: {e}")
        pytest.fail(f"Digital twin test failed: {e}")

if __name__ == "__main__":
    # Run tests directly
    print("🚀 Running Enhanced AI Chatbot Feature Tests...")
    print("=" * 60)
    
    test_imports()
    test_notebook_functionality()
    test_git_integration()
    test_user_profiles()
    asyncio.run(test_chain_of_thought())
    test_digital_twin()
    
    print("=" * 60)
    print("🎉 All tests completed successfully!")
