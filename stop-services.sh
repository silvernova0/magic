#!/bin/bash
# Stop JankBuild services

cd /home/social/magicapp

echo "Stopping JankBuild services..."

# Kill by PID files if they exist
if [ -f .api-server.pid ]; then
    kill $(cat .api-server.pid) 2>/dev/null
    rm .api-server.pid
fi

if [ -f .nextjs.pid ]; then
    kill $(cat .nextjs.pid) 2>/dev/null
    rm .nextjs.pid
fi

# Fallback: kill by process name
pkill -f "api-server.py" 2>/dev/null
pkill -f "next dev" 2>/dev/null

echo "✅ Services stopped!"

