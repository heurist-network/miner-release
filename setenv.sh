#!/bin/bash

# This script sets the PYTHONPATH environment variable to include the directory
# where the script is located, which should be the root directory of the miner.

# Get the directory of the current script.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Add the script directory to PYTHONPATH.
export PYTHONPATH="${PYTHONPATH}:${DIR}"
# Print the new PYTHONPATH.
echo "PYTHONPATH set to ${PYTHONPATH}"
