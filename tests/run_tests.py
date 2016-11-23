
import sys
import unittest
import rpc_tests

def run_tests(engine):

    engine.log_debug("Getting test suite...")
    suite = rpc_tests.get_tests_by_app_id(engine.app_id, engine.adobe)

    engine.log_debug("Running test suite...")
    unittest.TextTestRunner().run(suite)

    engine.log_debug("Testing finished.")
