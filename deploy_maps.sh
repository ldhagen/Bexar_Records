#!/bin/bash

# ==================================================================================
# Map Generation and Deployment Script
# 
# Description:
#   This script automates the process of generating interactive jail booking and 
#   release maps using `run_mapping_standalone.py` and deploying them to a remote 
#   web server via rsync.
#
# Dependencies:
#   - Python 3 environment with pandas, folium, and requests.
#   - Local Nominatim geocoding service running on http://localhost:8095 
#     (required by `run_mapping_standalone.py`).
#   - SSH access to the remote web server.
#
# Configuration:
#   Update the "Web Host Details" section below with your server's specific 
#   information or ensure SSH keys are configured for password-less login.
# ==================================================================================

# --- Configuration ---
# Project Directory
PROJECT_DIR="/var/tmp/ldh/pkl_storage"

# Web Host Details (EDIT THESE)
REMOTE_USER="your_username"
REMOTE_HOST="your_domain.com" # or the IP address provided by WebHostHub
REMOTE_DIR="public_html/maps/" # The folder on the server where maps should go
SSH_PORT="2222" # WebHostHub often uses port 2222 for SSH/SFTP. Check your specific port.

# Log File
LOG_FILE="$PROJECT_DIR/deploy.log"

# ---------------------

# Start Logging
{
    echo "========================================"
    echo "Starting deployment: $(date)"

    # 1. Go to directory
    cd "$PROJECT_DIR" || { echo "Failed to change directory"; exit 1; }

    # 2. (Optional) Run Data Fetching
    # If you have a script to download the CSVs, uncomment the next line:
    # python3 fetch_data.py 

    # 3. Generate Maps
    echo "Running mapping script..."
    /usr/bin/python3 run_mapping_standalone.py

    # Check if files were created
    if [[ -f "booking_map_standalone.html" && -f "release_map_standalone.html" ]]; then
        echo "Maps generated successfully."
    else
        echo "Error: Map files were not generated."
        exit 1
    fi

    # 4. Upload via Rsync
    # This transfers the files securely. 
    # It requires SSH keys to be set up (see instructions).
    echo "Uploading to $REMOTE_HOST..."
    
    rsync -avz -e "ssh -p $SSH_PORT" \
        booking_map_standalone.html \
        release_map_standalone.html \
        $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR

    if [ $? -eq 0 ]; then
        echo "Upload complete!"
    else
        echo "Upload failed. Please check SSH connection and credentials."
        exit 1
    fi

    echo "Finished: $(date)"
    echo "========================================"

} >> "$LOG_FILE" 2>&1
