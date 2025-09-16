#!/usr/bin/env python3
"""
Simple script to verify the FastAPI application can start.

This script imports and validates the FastAPI app without actually
running the server, ensuring all components are properly configured.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Verify FastAPI app can be imported and initialized."""
    print("🚀 Verifying FastAPI Application Setup")
    print("=" * 45)
    
    try:
        print("📦 Importing FastAPI application...")
        from api.main import app
        
        print(f"✅ App Title: {app.title}")
        print(f"✅ App Description: {app.description}")
        print(f"✅ App Version: {app.version}")
        
        # Count routes
        route_count = len([r for r in app.routes if hasattr(r, 'path')])
        print(f"✅ Registered Routes: {route_count}")
        
        # List core endpoints
        print("\n📝 Core Endpoints:")
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ", ".join(route.methods)
                print(f"  • {methods}: {route.path}")
        
        print("\n🎉 FastAPI application verification successful!")
        print("\n🚀 To start the server, run:")
        print("   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
        
        return 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed:")
        print("   pip install fastapi uvicorn sqlmodel burr pydantic python-dotenv")
        return 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())