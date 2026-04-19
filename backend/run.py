#!/usr/bin/env python3
import sys
import os

# Ensure we're running from the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

# Import from a specific module path to avoid any shadowing
from app import create_app as _create_app

flask_app = _create_app()

if __name__ == "__main__":
    flask_app.run(debug=True, host="0.0.0.0", port=5001)
