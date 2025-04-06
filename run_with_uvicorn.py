import os
import sys
import uvicorn

def run_server():    
    config = {
        "app": "wsgi:app",
        "host": "127.0.0.1",
        "port": 8000,
        "workers": 1,
        "interface": "wsgi",
        "loop": "asyncio",
        "limit_concurrency": 1000,
        "timeout_keep_alive": 5,
        "log_level": "info",
        "access_log": True
    }
    
    print("Starting server in WSGI mode with single worker")
    uvicorn.run(**config)

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    run_server()
