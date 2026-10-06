import sys
import os

# Add src to python path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting MediDesk server at http://127.0.0.1:{port}...")
    app.run(host='127.0.0.1', port=port, debug=False)
