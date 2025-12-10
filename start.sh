#!/bin/bash

# EPUB to PDF Converter - Startup Script
# This script starts the application using Docker Compose

echo "Starting EPUB to PDF Converter..."

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
elif command -v docker &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    echo "Error: Neither docker-compose nor docker compose is available"
    exit 1
fi

# Start the services
$DOCKER_CMD up --build

echo "Application is running at http://localhost:7860"