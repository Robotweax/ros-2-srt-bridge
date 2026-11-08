from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from source_payload import canonical, fingerprint


def fixture(route):
    m = NS(header=NS(stamp=NS(sec=1, nanosec=2), frame_id='demo_imu' if route == 1 else 'demo_base'))
    if route == 1:
        m.orientation=NS(x=0., y=0., z=0., w=1.)
        m.angular_velocity=NS(x=200., y=0., z=1.)
        m.linear_acceleration=NS(x=0., y=0., z=9.81)
        m.orientation_covariance=m.angular_velocity_covariance=m.linear_acceleration_covariance=[0.]*9
    else:
        m.name=['joint_'+str(i+1) for i in range(6)]
        m.position=[i+.001 for i in range(6)];m.velocity=[200.]*6;m.effort=[0.]*6
    return m


class SourcePayloadTests(unittest.TestCase):
    def test_golden_fields(self):
        for route, size, digest in GOLDEN:
            m=fixture(route)
            self.assertEqual(len(canonical(m, route)), size)
            self.assertEqual(fingerprint(m, route), digest)

    def test_hash_includes_stamp_covariance_and_arrays(self):
        for route in (1, 2):
            m=fixture(route);original=fingerprint(m,route);m.header.stamp.sec=-1
            self.assertNotEqual(fingerprint(m,route),original)
        m=fixture(1);original=fingerprint(m,1);m.angular_velocity_covariance=[1.]*9
        self.assertNotEqual(fingerprint(m,1),original)
        m=fixture(2);original=fingerprint(m,2);m.effort[5]=1.
        self.assertNotEqual(fingerprint(m,2),original)

    def test_invalid_bounds(self):
        for route in (1,2):
            m=fixture(route);m.header.frame_id='é'*33
            with self.assertRaises(ValueError):canonical(m,route)
            m=fixture(route);m.header.stamp.nanosec=1_000_000_000
            with self.assertRaises(ValueError):canonical(m,route)
        m=fixture(2);m.position=[0.]
        with self.assertRaises(ValueError):canonical(m,2)
        with self.assertRaises(ValueError):canonical(fixture(1),3)


GOLDEN=[(1,320,'9b9fb4ab825de5547904f18cecdd6d3a3c2a8ad02788c3830367d59c1e86555d'),(2,251,'86afad2bc7c769a1aee62395b7c49a5b4ab90fdf131087065a09a37ee50f4ef3')]
