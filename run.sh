#!/usr/bin/env bash

# Setup and run script for the Flask app.  Designed to be executed from within
# this directory (now named VulnappbyBunnyWalker) after it has been copied to a Linux/Kali machine.
# If the original template is still available as ../login-form-20/login-form-20
# it will attempt to copy assets; otherwise it assumes the static files are
# already present.

set -euo pipefail

# working dir should be VulnappbyBunnyWalker
cd "$(dirname "$0")" || exit 1

# optionally copy assets from original template if they aren't present
if [ ! -d static/css ] || [ ! -d static/js ]; then
    SRC="$(dirname "$PWD")/login-form-20/login-form-20"
    if [ -d "$SRC" ]; then
        echo "Copying static assets from $SRC..."
        mkdir -p static
        cp -r "$SRC/css" static/
        cp -r "$SRC/js" static/
        cp -r "$SRC/images" static/
        cp -r "$SRC/fonts" static/
    else
        echo "Static assets not found and source template is missing."
        echo "Make sure css/js/images/fonts are under static/ before running."
        # continue anyway; dependencies may still install
    fi
fi

# create/activate venv
if [ ! -x "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv venv || { echo "python3 failed to create venv"; ls -l venv; exit 1; }
    elif command -v python >/dev/null 2>&1; then
        python -m venv venv || { echo "python failed to create venv"; ls -l venv; exit 1; }
    else
        echo "ERROR: Python 3 is not installed. Install it (e.g. sudo apt install python3 python3-venv) and rerun."
        exit 1
    fi
fi

# shellcheck source=/dev/null
if [ -x "venv/bin/activate" ]; then
    echo "activating virtualenv..."
    source venv/bin/activate
else
    echo "ERROR: virtualenv activation script not found; venv creation probably failed."
    echo "venv contents:"; ls -R venv || true
    exit 1
fi

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Creating uploads directory..."
mkdir -p uploads

echo "Creating logs directory..."
mkdir -p logs

echo "Starting Flask server (ctrl-c to stop)..."
python app.py
