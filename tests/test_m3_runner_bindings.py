"""Python scopes are fixed for the entire function, including finally blocks."""
import inspect
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import m3_capture
import run_m3


class RunnerBindingTests(unittest.TestCase):
    def test_packet_parser_remains_globally_resolved_before_sender_finalization(self):
        # An unaliased later import makes every earlier packet-parser call an
        # unbound LOCAL, even when the sender flag is false. Check Python's real
        # compiled scope, not merely whether '--help' exits successfully.
        bindings=inspect.getclosurevars(run_m3.main)
        self.assertIs(bindings.globals.get('summarize'),m3_capture.summarize)
        self.assertNotIn('summarize',run_m3.main.__code__.co_varnames)


if __name__=='__main__':unittest.main()
