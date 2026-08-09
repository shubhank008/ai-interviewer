"""Run the Phase 9 executable evidence path."""

import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, "tests")
suite = unittest.defaultTestLoader.loadTestsFromName("test_phase9_production")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
