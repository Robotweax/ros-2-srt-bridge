import copy
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_dds_discovery_packets import decode,assess


class PacketTests(unittest.TestCase):
    def test_native_payload_requires_exact_shape_role_magic_and_origin(self):
        payload=struct.pack('!4sIIQQ',bytes(4),0x48454c31,2,1,10)
        self.assertEqual(decode(payload,2)['sent_ns'],10)
        for bad in (payload[:-1],payload+b'\0',b'X'+payload[1:],payload[:7]+b'X'+payload[8:]):
            with self.assertRaises(ValueError):decode(bad,2)
        with self.assertRaises(ValueError):decode(payload,1)

    def fixture(self):
        result=dict(case='fragment-cut',initial=dict(operator=dict(writer='op'),robot=dict(writer='bot')),hold=dict(begin_ns=10),remove=dict(begin_ns=20))
        pubs=[dict(endpoint='op',topic='M3FragmentHelloOperator',frame=1),dict(endpoint='bot',topic='M3FragmentHelloRobot',frame=100)]
        parsed={r:dict(rows=copy.deepcopy(pubs),fragment_frames=4) for r in ('operator','robot')}
        messages={r:[dict(writer='bot',sequence=i,payload_sha256=str(i),sent_ns=15,frame=i) for i in range(1,21)] for r in parsed}
        return result,parsed,messages

    def test_matching_data_must_precede_complete_advertisement_and_have_in_cut_origins(self):
        args=self.fixture();self.assertEqual(assess(*args)['robot_hellos_before_first_complete_advertisement'],20)
        for defect in ('hash','late_origin','early_advert','no_fragments'):
            r,p,m=self.fixture()
            if defect=='hash':m['robot'][0]['payload_sha256']='wrong'
            elif defect=='late_origin':m['operator'][0]['sent_ns']=30
            elif defect=='early_advert':p['operator']['rows'][1]['frame']=1
            else:p['robot']['fragment_frames']=0
            with self.subTest(defect=defect),self.assertRaises(ValueError):assess(r,p,m)
