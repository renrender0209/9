#!/bin/bash

# Build script for Render deployment
set -e

echo "Starting build process..."

# Install root dependencies
echo "Installing root dependencies..."
npm install --prefer-offline

# Navigate to client directory and install dependencies
echo "Installing client dependencies..."
cd client
npm install --prefer-offline

# Build the client
echo "Building client application..."
npm run build

# Go back to root
cd ..

echo "Build completed successfully!"