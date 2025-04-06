#!/bin/bash

SERVER_TYPE=${1:-uvicorn}

echo "Using $SERVER_TYPE to start app..."

while true; do
    case $SERVER_TYPE in
        uvicorn)
            python3 run_with_uvicorn.py
            ;;
        waitress)
            python3 run_with_waitress.py
            ;;
        *)
            echo "Unsupported server type: $SERVER_TYPE"
            echo "Supported server types are: uvicorn, waitress"
            exit 1
            ;;
    esac
    
    echo "Application crashed or stopped. Restarting..."
    sleep 2
done
