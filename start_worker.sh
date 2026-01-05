#!/bin/bash

# Fix for macOS "objc_initializeAfterForkError"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

echo "Starting 4 RQ Workers..."

# Function to kill all background jobs on exit
cleanup() {
    echo "Shutting down workers..."
    pkill -P $$
    wait
    echo "All workers stopped."
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start 4 workers in background
for i in {1..4}; do
    python -m src.worker &
    echo "Worker $i started with PID $!"
done

echo "Workers are running. Press Ctrl+C to stop all."

# Wait for all background processes
wait
