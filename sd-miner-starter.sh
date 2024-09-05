#!/bin/bash

# Create .env file from environment variables and count MINER_IDs
> /app/.env
MINER_COUNT=0
for i in {0..9}; do
    var_name="MINER_ID_$i"
    if [ ! -z "${!var_name}" ]; then
        echo "$var_name=${!var_name}" >> /app/.env
        MINER_COUNT=$((MINER_COUNT + 1))
    fi
done

# Update num_cuda_devices in config.toml
sed -i "s/num_cuda_devices = .*/num_cuda_devices = $MINER_COUNT/" /app/config.toml

# Set default values for arguments
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
AUTO_CONFIRM=${AUTO_CONFIRM:-"yes"}
EXCLUDE_SDXL=${EXCLUDE_SDXL:-"no"}
SKIP_SIGNATURE=${SKIP_SIGNATURE:-"yes"}
SKIP_CHECKSUM=${SKIP_CHECKSUM:-"yes"}
MODEL_ID=${MODEL_ID:-""}
CUDA_DEVICE_ID=${CUDA_DEVICE_ID:-""}

# Construct the command
CMD="python3 sd-miner-v1.3.1.py --log-level $LOG_LEVEL"

# Add optional flags
[ "$AUTO_CONFIRM" = "yes" ] && CMD="$CMD --auto-confirm yes"
[ "$EXCLUDE_SDXL" = "yes" ] && CMD="$CMD --exclude-sdxl"
[ "$SKIP_SIGNATURE" = "yes" ] && CMD="$CMD --skip-signature"
[ "$SKIP_CHECKSUM" = "yes" ] && CMD="$CMD --skip-checksum"
[ ! -z "$MODEL_ID" ] && CMD="$CMD --model-id $MODEL_ID"
[ ! -z "$CUDA_DEVICE_ID" ] && CMD="$CMD --cuda-device-id $CUDA_DEVICE_ID"

# Execute the command
exec $CMD