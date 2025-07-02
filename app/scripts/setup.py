#!/usr/bin/env python3
"""
Setup script for AgencyCoachAI development environment.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False

def setup_virtual_environment():
    """Set up Python virtual environment."""
    print("Setting up Python virtual environment...")
    
    # Create virtual environment
    if not run_command("python3 -m venv venv"):
        print("Failed to create virtual environment")
        return False
    
    print("Virtual environment created successfully!")
    return True

def install_backend_dependencies():
    """Install backend dependencies."""
    print("Installing backend dependencies...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", cwd=backend_dir):
        print("Failed to install backend dependencies")
        return False
    
    print("Backend dependencies installed!")
    return True

def install_frontend_dependencies():
    """Install frontend dependencies."""
    print("Installing frontend dependencies...")
    
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", cwd=frontend_dir):
        print("Failed to install frontend dependencies")
        return False
    
    print("Frontend dependencies installed!")
    return True

def setup_environment_files():
    """Set up environment configuration files."""
    print("Setting up environment files...")
    
    project_root = Path(__file__).parent.parent.parent
    
    # Copy main .env.example to .env if it doesn't exist
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print(f"✓ Created {env_file}")
    
    # Copy frontend .env.example to .env
    frontend_env_example = project_root / "app" / "frontend" / ".env.example"
    frontend_env = project_root / "app" / "frontend" / ".env"
    
    if not frontend_env.exists() and frontend_env_example.exists():
        import shutil
        shutil.copy(frontend_env_example, frontend_env)
        print(f"✓ Created {frontend_env}")
    
    print("Environment files set up!")
    return True

def initialize_database():
    """Initialize the database."""
    print("Initializing database...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    
    # Run database initialization
    if not run_command("python -c 'import asyncio; from database import init_db; asyncio.run(init_db())'", cwd=backend_dir):
        print("Failed to initialize database")
        return False
    
    print("Database initialized!")
    return True

def main():
    """Main setup function."""
    print("🚀 Setting up AgencyCoachAI development environment...")
    print()
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: Not running in a virtual environment")
        print("It's recommended to run this in a virtual environment")
        print()
    
    success = True
    
    # Run setup steps
    success &= setup_environment_files()
    success &= install_backend_dependencies()
    success &= install_frontend_dependencies()
    
    # Try to initialize database (may fail if environment not configured)
    try:
        initialize_database()
    except Exception as e:
        print(f"⚠️  Database initialization skipped: {e}")
        print("Please configure your .env file and run database initialization manually")
    
    print()
    if success:
        print("🎉 Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Configure your API keys in .env and app/frontend/.env")
        print("2. Start the backend: cd app/backend && uvicorn main:app --reload")
        print("3. Start the frontend: cd app/frontend && chainlit run app.py")
        print()
        print("See docs/BUILD_GUIDE.md for detailed instructions.")
    else:
        print("❌ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()