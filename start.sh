#!/bin/bash

# Start the server
echo "Starting YouTube Clone server..."
cd /home/runner/workspace
node server/index.js &

# Keep the script running
wait