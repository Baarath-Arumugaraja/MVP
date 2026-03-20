import sys, os

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

import importlib.util
spec = importlib.util.spec_from_file_location("backend_app", os.path.join(backend_dir, "app.py"))
backend_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_app)
app = backend_app.app
