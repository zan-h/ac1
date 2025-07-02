#!/usr/bin/env python3
"""
Development runner for AgencyCoachAI - starts both backend and frontend.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import signal
import threading

class DevRunner:
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent.parent.parent
        
    def start_backend(self):
        """Start the FastAPI backend."""
        backend_dir = self.project_root / "app" / "backend"
        
        print("🔧 Starting FastAPI backend...")
        
        try:
            process = subprocess.Popen(
                ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(("Backend", process))
            
            # Monitor output in a separate thread
            def monitor_backend():
                for line in iter(process.stdout.readline, ''):
                    print(f"[Backend] {line.strip()}")
                
            threading.Thread(target=monitor_backend, daemon=True).start()
            
            print("✓ Backend started on http://localhost:8000")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    def start_frontend(self):
        """Start the Chainlit frontend."""
        frontend_dir = self.project_root / "app" / "frontend"
        
        print("🎨 Starting Chainlit frontend...")
        
        try:
            process = subprocess.Popen(
                ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8001"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(("Frontend", process))
            
            # Monitor output in a separate thread
            def monitor_frontend():
                for line in iter(process.stdout.readline, ''):
                    print(f"[Frontend] {line.strip()}")
                
            threading.Thread(target=monitor_frontend, daemon=True).start()
            
            print("✓ Frontend started on http://localhost:8001")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\\n🛑 Shutting down development servers...")
        self.stop_all()
        sys.exit(0)
    
    def stop_all(self):
        """Stop all running processes."""
        for name, process in self.processes:
            if process.poll() is None:  # Process is still running
                print(f"Stopping {name}...")
                process.terminate()
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name}...")
                    process.kill()
    
    def run(self):
        """Run the development environment."""
        print("🚀 Starting AgencyCoachAI development environment...")
        print()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check if environment files exist
        env_file = self.project_root / ".env"
        frontend_env = self.project_root / "app" / "frontend" / ".env"
        
        if not env_file.exists():
            print("⚠️  No .env file found. Please run setup.py first or copy .env.example to .env")
            return False
        
        if not frontend_env.exists():
            print("⚠️  No frontend .env file found. Please copy app/frontend/.env.example to app/frontend/.env")
            return False
        
        # Start services
        if not self.start_backend():
            return False
        
        # Wait a moment for backend to start
        time.sleep(2)
        
        if not self.start_frontend():
            self.stop_all()
            return False
        
        print()
        print("🎉 Development environment is running!")
        print()
        print("Services:")
        print("- Backend API: http://localhost:8000")
        print("- Frontend UI: http://localhost:8001") 
        print("- API Docs: http://localhost:8000/docs")
        print()
        print("Press Ctrl+C to stop all services")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
                
                # Check if any process has died
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"❌ {name} has stopped unexpectedly")
                        self.stop_all()
                        return False
                        
        except KeyboardInterrupt:
            pass

def main():
    """Main entry point."""
    runner = DevRunner()
    success = runner.run()
    
    if not success:
        print("❌ Development environment failed to start")
        sys.exit(1)

if __name__ == "__main__":
    main()