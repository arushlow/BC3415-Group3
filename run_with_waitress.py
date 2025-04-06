import os
import sys

from waitress import serve

from app import app


def run_server():    
    print("Starting server with Waitress (pure WSGI server)")
    serve(app, host="127.0.0.1", port=8000, threads=1)

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    run_server()
