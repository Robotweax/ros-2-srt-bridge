import dataclasses
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sensor_fault import Selection, commands, install
from m3_sensor_fault_probe import population


class SensorFaultTests(unittest.TestCase):
    def selection(self, **changes):
        return dataclasses.replace(Selection(0x7ffffffe, 1, (2, 3), (3, 4), 123), **changes)

    def test_group_is_relative_to_explicit_origin_and_wraps(self):
        self.assertEqual([t['sequence'] for t in self.selection().targets()], [4, 5])
        self.assertEqual([t['position'] for t in self.selection().targets()], [2, 3])

    def test_invalid_or_ambiguous_selection(self):
        for changes in ({'initial_sequence': True}, {'initial_sequence': -1},
                        {'row': 1 << 28}, {'row': -1}, {'positions': (0, 0)},
                        {'positions': (0, 1, 2)}, {'positions': (4,)},
                        {'positions': (True,)}, {'message_numbers': (0, 4)},
                        {'message_numbers': (1,)}, {'socket_id': 0},
                        {'source_port': 10080}, {'destination_port': 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.selection(**changes)

    def test_filters_guard_header_and_parity(self):
        argv = commands(self.selection(), '10.0.0.1', '10.0.0.2')
        self.assertEqual(len(argv), 2)
        for a in argv:
            text = ' '.join(a)
            self.assertIn('u8 0x45 0xff at 0', text)
            self.assertIn('u16 0 0x3fff at 6', text)
            self.assertIn('u32 0x7b 0xffffffff at 40', text)
            self.assertIn('0x3ffffff at 32', text)
            self.assertEqual(a[-2:], ['action', 'drop'])
        for peer in ('127.0.0.1', '::1', '224.0.0.1', '10.0.0.1'):
            with self.assertRaises(ValueError):
                commands(self.selection(), '10.0.0.1', peer)

    def test_probe_contains_parity_sharing_selected_last_sequence(self):
        s = self.selection(); rows = population(s)
        source = next(r for r in rows if r['label'] == 'source-3')
        parity = next(r for r in rows if r['label'].startswith('parity'))
        self.assertEqual(source['sequence'], parity['sequence'])
        self.assertEqual(parity['message'], 0)
        self.assertIn('retransmitted-target', [r['label'] for r in rows])

    def test_partial_install_failure_removes_owned_hook(self):
        class Lab:
            containers = {'robot': 'r', 'operator': 'o'}
            addresses = {'robot': '10.0.0.1', 'operator': '10.0.0.2'}
            removed = False
            def inside(self, role, label, argv):
                if label == 'sensor-fault-qdisc-before':
                    return '[]'
                if label == 'sensor-fault-install-1':
                    raise RuntimeError('second rule fails')
                if label == 'sensor-fault-remove':
                    self.removed = True
                if label == 'sensor-fault-restored':
                    return '[]'
                if argv[:2] == ['python3', '-c']:
                    return json.dumps(dict(exit_code=0, begin_ns=1, end_ns=2))
                return ''
        lab = Lab()
        with self.assertRaises(RuntimeError):
            install(lab, self.selection())
        self.assertTrue(lab.removed)
