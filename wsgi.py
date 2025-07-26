import sys
import os

# Tambahkan path ke folder project

current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
path = project_root
if path not in sys.path:
    sys.path.insert(0, path)

# Set working directory
os.chdir(path)

# Import app dari app.py
from app import app as application
