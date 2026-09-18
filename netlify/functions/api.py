import sys
import os

# Add your root directory to path so it can find app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import handler