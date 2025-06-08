#!/bin/bash

# Exit if any command fails
#set -e
deactivate

# Create virtual environment
python -m venv .bike_venv

# Activate the virtual environment
source .bike_venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Add Jupyter kernel
python -m ipykernel install --user --name=.bike_venv --display-name "Python (.bike_venv)"
