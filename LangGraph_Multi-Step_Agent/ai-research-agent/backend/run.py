#!/usr/bin/env python
import uvicorn
import sys
import os

# Add the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AI Research Agent Backend")
    print("=" * 60)
    print(f"📍 Server will run at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🔧 Test API: http://localhost:8000/api/test")
    print(f"💚 Health Check: http://localhost:8000/health")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /                - Root endpoint")
    print("  GET  /health          - Health check")
    print("  GET  /api/health      - API health check")
    print("  GET  /api/test        - Test endpoint")
    print("  POST /api/chat        - Send message")
    print("  POST /api/chat/stream - Stream message")
    print("  POST /api/chat/simple - Simple test endpoint")
    print("=" * 60)
    print("\n✅ Starting server...\n")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )