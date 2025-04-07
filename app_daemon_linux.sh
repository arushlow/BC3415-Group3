#!/bin/bash

SERVER_TYPE=${1:-gunicorn}

echo "Using $SERVER_TYPE to start app..."

while true; do
    case $SERVER_TYPE in
        gunicorn)
            python run_with_gunicorn.py
            ;;
        waitress)
            python run_with_waitress.py
            ;;
        *)
            echo "Unsupported server type: $SERVER_TYPE"
            echo "Supported server types are: gunicorn, waitress"
            exit 1
            ;;
    esac
    
    echo "Application crashed or stopped. Restarting..."
done
