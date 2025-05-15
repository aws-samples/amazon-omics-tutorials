#!/bin/bash

# Script to run the HealthOmics analyzer
# Usage: ./run_analyzer.sh <run-id1> [run-id2 run-id3 ...] [--headroom <value>]

# Get the directory where the script is located, regardless of where it's called from
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# Default headroom value
HEADROOM=0.1
RUN_IDS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --headroom)
            shift
            if [[ -z "$1" ]]; then
                echo "Error: --headroom requires a value"
                exit 1
            fi
            # Validate that headroom is a positive float between 0.0 and 1.0
            if [[ ! "$1" =~ ^[0-9]*\.?[0-9]+$ ]] || (( $(echo "$1 < 0.0" | bc -l) )) || (( $(echo "$1 > 1.0" | bc -l) )); then
                echo "Error: headroom must be a positive float between 0.0 and 1.0"
                exit 1
            fi
            HEADROOM="$1"
            shift
            ;;
        *)
            # Add to run IDs array
            RUN_IDS+=("$1")
            shift
            ;;
    esac
done

# Check if at least one run-id is provided
if [ ${#RUN_IDS[@]} -eq 0 ]; then
    echo "Error: at least one run-id is required"
    echo "Usage: ./run_analyzer.sh <run-id1> [run-id2 run-id3 ...] [--headroom <value>]"
    echo "  <run-id>: One or more HealthOmics run IDs (at least one required)"
    echo "  --headroom <value>: Optional positive float between 0.0 and 1.0 (default: 0.1)"
    exit 1
fi

# Check if virtual environment exists, if not create it and install required packages
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating one at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    
    echo "Installing aws-healthomics-tools..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install aws-healthomics-tools
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install aws-healthomics-tools. Please check your internet connection and try again."
        exit 1
    fi
    
    echo "Virtual environment setup complete."
fi

# Build the command using the absolute path to the virtual environment
CMD="$VENV_DIR/bin/python -m omics.cli.run_analyzer -b"

# Add all run IDs to the command
for run_id in "${RUN_IDS[@]}"; do
    CMD="$CMD $run_id"
done

# Add headroom parameter
CMD="$CMD --headroom $HEADROOM"

# Display and run the command
echo "Running analyzer for run-ids: ${RUN_IDS[*]} with headroom: $HEADROOM"
echo "Executing: $CMD"
eval "$CMD"
