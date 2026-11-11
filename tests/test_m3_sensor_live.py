import copy
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sensor_live import validate_outcomes, header


def outcomes(losses):
    stats = dict(data_sent=0,retransmitted=0,filter_extra_sent=0,filter_extra_received=0,filter_supplied=0,filter_loss=0,undecryptable=0)
    sender = dict(initial_stats=stats.copy(), final_stats=dict(stats, data_sent=16, filter_extra_sent=4), connected=True,
                  entries=[dict(id=i,msgno=i+1) for i in range(16)])
    receiver = dict(initial_stats=stats.copy(), final_stats=dict(stats, filter_extra_received=4, filter_supplied=int(losses==1), filter_loss=0), connected=True,
                    entries=[dict(id=i,msgno=i+1) for i in range(16) if losses!=2 or i not in (6,7)])
    return sender,receiver


class SensorLiveTests(unittest.TestCase):
    def test_repair_and_irrecoverable_populations(self):
        for losses,count in ((0,16),(1,16),(2,14)):
            self.assertEqual(len(validate_outcomes(*outcomes(losses),losses)['delivered_ids']),count)

    def test_missing_duplicate_wrong_identity_and_missing_repair_rejected(self):
        for change in ('missing','duplicate','wrong-msg','no-repair','retransmit','undecryptable','prearm','nonzero-loss-report'):
            a,b=copy.deepcopy(outcomes(1))
            if change=='missing':b['entries'].pop()
            elif change=='duplicate':b['entries'].append(b['entries'][0])
            elif change=='wrong-msg':b['entries'][0]['msgno']=999
            elif change=='no-repair':b['final_stats']['filter_supplied']=0
            elif change=='retransmit':a['final_stats']['retransmitted']=1
            elif change=='undecryptable':b['final_stats']['undecryptable']=1
            elif change=='nonzero-loss-report':b['final_stats']['filter_loss']=2
            else:a['initial_stats']['data_sent']=1
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_outcomes(a,b,1)

    def test_two_missing_ids_do_not_become_provider_loss_counter(self):
        result=validate_outcomes(*outcomes(2),2)
        self.assertEqual(result['missing_ids'],[6,7])
        self.assertEqual(result['filter_loss_reported'],0)

    def test_header_preserves_parity_and_socket_identity(self):
        frame=bytearray(58);frame[12:14]=b'\x08\x00';frame[14]=0x45;frame[23]=17
        struct.pack_into('!HHH',frame,34,39781,10081,24)
        struct.pack_into('!IIII',frame,42,123,0xc0000000,0,987)
        self.assertEqual(header(frame),(123,0,987,False))
        struct.pack_into('!I',frame,42,0x80000000)
        self.assertIsNone(header(frame))
        frame[14]=0x46
        with self.assertRaises(ValueError):header(frame)
