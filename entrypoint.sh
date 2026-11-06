#!/bin/sh

# Start the stats service in the background
python3 /app/stats_service.py &

# Check if the required VirtIO serial port exists
if [ -e /dev/virtio-ports/org.qemu.guest_agent.0 ]; then
  echo "VirtIO serial port found. Starting QEMU Guest Agent..."
  exec /usr/bin/qemu-ga "$@"
else
  echo "VirtIO serial port NOT found. Running in mock mode for testing/visibility."
  # Keep the container alive so that the stats service can be tested
  sleep infinity
fi
