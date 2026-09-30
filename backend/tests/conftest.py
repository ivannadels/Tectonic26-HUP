import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DEMO_PASSWORD", "test-pass-123")
os.environ.setdefault("USE_LLM", "false")
