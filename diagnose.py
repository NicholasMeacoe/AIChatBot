#!/usr/bin/env python3
"""
Diagnostic script to check if the enhanced upload functionality is properly set up
"""

import os
import sys
import importlib.util

def check_imports():
    """Check if all required imports are available"""
    print("🔍 Checking imports...")
    
    required_modules = [
        'flask', 'werkzeug', 'google.generativeai', 'PIL', 'uuid', 'datetime'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing.append(module)
    
    return len(missing) == 0

def check_directories():
    """Check if required directories exist"""
    print("\n📁 Checking directories...")
    
    dirs = ['allowed_context', 'templates', 'static']
    all_exist = True
    
    for dir_name in dirs:
        if os.path.exists(dir_name):
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (missing)")
            all_exist = False
    
    return all_exist

def check_files():
    """Check if required files exist"""
    print("\n📄 Checking files...")
    
    files = [
        'app.py',
        'templates/index.html',
        '.env'
    ]
    
    all_exist = True
    for file_name in files:
        if os.path.exists(file_name):
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} (missing)")
            all_exist = False
    
    return all_exist

def check_app_structure():
    """Check if the app has the required routes"""
    print("\n🔧 Checking app structure...")
    
    try:
        from app import gemini_app
        app = gemini_app.app
        
        # Check if routes exist
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.methods} {rule.rule}")
        
        required_routes = [
            '/api/context/upload',
            '/api/context/check_images',
            '/api/chat'
        ]
        
        print("  Available routes:")
        for route in sorted(routes):
            print(f"    {route}")
        
        missing_routes = []
        for req_route in required_routes:
            found = any(req_route in route for route in routes)
            if found:
                print(f"  ✅ {req_route}")
            else:
                print(f"  ❌ {req_route} (missing)")
                missing_routes.append(req_route)
        
        return len(missing_routes) == 0
        
    except Exception as e:
        print(f"  ❌ Error checking app structure: {e}")
        return False

def check_environment():
    """Check environment variables"""
    print("\n🌍 Checking environment...")
    
    env_vars = ['GOOGLE_API_KEY']
    all_set = True
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var} (set)")
        else:
            print(f"  ⚠️  {var} (not set - some features may not work)")
            # Don't mark as failure since app can still run for testing
    
    return True

def main():
    """Run all diagnostic checks"""
    print("🏥 AIChatBot Enhanced Upload Diagnostics")
    print("=" * 50)
    
    checks = [
        ("Imports", check_imports),
        ("Directories", check_directories),
        ("Files", check_files),
        ("App Structure", check_app_structure),
        ("Environment", check_environment)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ Error in {name} check: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary:")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! The enhanced upload functionality should work.")
        print("\n🚀 To start the server, run:")
        print("   python start_test.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\n🔧 Common fixes:")
        print("   • Install missing packages: pip install -r requirements.txt")
        print("   • Create missing directories: mkdir allowed_context")
        print("   • Set environment variables in .env file")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
