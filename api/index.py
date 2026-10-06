import os
import sys

# Compute project root and src directory paths
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_dir = os.path.join(root_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Serverless environment: ensure SQLite db is writable in /tmp
if not os.environ.get('DATABASE_PATH'):
    os.environ['DATABASE_PATH'] = '/tmp/medidesk.db'

# Import the initialized Flask WSGI app
from app import app
