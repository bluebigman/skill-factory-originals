import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
import main as m
sys.exit(0 if m._run_selftest() == 0 else 1)
