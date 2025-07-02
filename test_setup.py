#!/usr/bin/env python3
"""
Quick test to verify the AgencyCoachAI setup is ready.
"""

import sys
import os
from pathlib import Path

def test_python_version():
    """Test Python version compatibility."""
    print("🐍 Testing Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is too old (need 3.8+)")
        return False

def test_project_structure():
    """Test project structure is correct."""
    print("📁 Testing project structure...")
    
    required_paths = [
        "app/frontend",
        "app/backend", 
        "app/scripts",
        "docs",
        ".env.example"
    ]
    
    project_root = Path(__file__).parent
    missing = []
    
    for path in required_paths:
        full_path = project_root / path
        if not full_path.exists():
            missing.append(path)
    
    if missing:
        print(f"✗ Missing required paths: {missing}")
        return False
    else:
        print("✓ Project structure is correct")
        return True

def test_environment_files():
    """Test environment configuration files."""
    print("⚙️  Testing environment files...")
    
    project_root = Path(__file__).parent
    env_files = [
        ".env.example",
        "app/frontend/.env.example"
    ]
    
    missing = []
    for env_file in env_files:
        if not (project_root / env_file).exists():
            missing.append(env_file)
    
    if missing:
        print(f"✗ Missing environment files: {missing}")
        return False
    else:
        print("✓ Environment files present")
        return True

def test_key_files():
    """Test that key implementation files exist."""
    print("📋 Testing key implementation files...")
    
    project_root = Path(__file__).parent
    key_files = [
        "app/backend/main.py",
        "app/backend/requirements.txt",
        "app/frontend/app.py",
        "app/frontend/requirements.txt",
        "app/scripts/setup.py",
        "app/scripts/run_dev.py"
    ]
    
    missing = []
    for file_path in key_files:
        if not (project_root / file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"✗ Missing key files: {missing}")
        return False
    else:
        print("✓ All key implementation files present")
        return True

def main():
    """Run all tests."""
    print("🧪 Testing AgencyCoachAI setup...\n")
    
    tests = [
        test_python_version,
        test_project_structure,
        test_environment_files,
        test_key_files
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    if all(results):
        print("🎉 All tests passed! The project is ready for setup.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your API keys")
        print("2. Copy app/frontend/.env.example to app/frontend/.env and configure")
        print("3. Run: python3 app/scripts/setup.py")
        print("4. Run: python3 app/scripts/run_dev.py")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)