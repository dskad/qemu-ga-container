#!/bin/sh

# Start the stats service in the background
python3 /app/stats_service.py &

# Start the QEMU Guest Agent
exec /usr/bin/qemu-ga "$@"
