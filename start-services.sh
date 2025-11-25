#!/bin/bash
# Start JankBuild services with nohup (persistent after logout)

cd /home/social/magicapp

echo "Starting JankBuild services..."

# Kill existing processes if they exist
pkill -f "api-server.py" 2>/dev/null
pkill -f "next dev" 2>/dev/null

# Start API server with nohup
echo "Starting API server..."
nohup /home/social/.virtualenvs/magicapp/bin/python scripts/active/pipeline/api-server.py > logs/api-server.log 2>&1 &
API_PID=$!
echo $API_PID > .api-server.pid

# Wait a moment for API to initialize
sleep 2

# Start Next.js web server with nohup
echo "Starting Next.js web server..."
nohup npm run dev > logs/nextjs.log 2>&1 &
WEB_PID=$!
echo $WEB_PID > .nextjs.pid

echo ""
echo "✅ Services started!"
echo "   API Server PID: $API_PID"
echo "   Next.js PID: $WEB_PID"
echo ""
echo "To view logs:"
echo "  tail -f logs/api-server.log"
echo "  tail -f logs/nextjs.log"
echo ""
echo "To stop services:"
echo "  ./stop-services.sh"
echo ""
echo "Services will continue running after you disconnect."

