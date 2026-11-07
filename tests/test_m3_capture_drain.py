from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_capture_drain import live_info,stable
from m3_capture import validate_tcpdump_footer
from m3_root_loss_burst import command,readback
import json


class DrainTests(unittest.TestCase):
    def test_complete_live_info_parses_and_partial_is_not_reused(self):
        self.assertIsNone(live_info('tcpdump: 1 packet captured, 2 packets received by filter'))
        self.assertEqual(live_info('tcpdump: 1 packet captured, 2 packets received by filter, 0 packets dropped by kernel\n'),dict(captured=1,filtered=2,kernel_drops=0))
    def snapshot(self,c=16,f=16,d=0):return {'robot':dict(counts=dict(captured=c,filtered=f,kernel_drops=d),identities=[[42,100]])}
    def test_stability_requires_equal_unchanged_counts_and_identity(self):
        self.assertTrue(stable(self.snapshot(),self.snapshot()))
        for b in (self.snapshot(f=17),self.snapshot(c=17,f=17),self.snapshot(d=1)):
            self.assertFalse(stable(self.snapshot(),b))
        b=self.snapshot();b['robot']['identities']=[[43,100]];self.assertFalse(stable(self.snapshot(),b))
        self.assertFalse(stable(None,self.snapshot()))
    def test_zero_kernel_drops_do_not_rescue_unread_file(self):
        r=validate_tcpdump_footer('0 packets captured\n16 packets received by filter\n0 packets dropped by kernel',0,require_nonempty=False)
        self.assertFalse(r['tcpdump_population_reconciled'])
    def test_child_command_is_change_and_explicit_loss_restore(self):
        a=command(100,1701);b=command(0,1701)
        self.assertEqual(a[:3],['tc','qdisc','change']);self.assertIn('100%',a);self.assertIn('0%',b);self.assertNotIn('replace',a)
    def test_burst_readback_validates_child_and_retained_root(self):
        class Lab:
            def inside(self,*args):return json.dumps([dict(root=True,kind='tbf',handle='1:',options=dict(rate=64000)),dict(kind='netem',handle='10:',parent='1:1',options=dict(limit=16,seed=1701,**{'loss-random':dict(loss=1)}))])
        self.assertEqual(readback(Lab(),'robot','read',1701,1)['root_config']['kind'],'tbf')
        with self.assertRaises(ValueError):readback(Lab(),'robot','read',1702,1)
        with self.assertRaises(ValueError):readback(Lab(),'robot','read',1701,0)

    def test_final_burst_readback_failure_still_restores(self):
        from unittest.mock import patch
        from m3_root_loss_burst import stop
        fault=dict(role='robot',seed=1701,before=dict(root_config={'kind':'tbf'}),install=dict(end_ns=10),restored=False)
        with patch('m3_root_loss_burst.readback',side_effect=[ValueError('read failed'),dict(root_config={'kind':'tbf'})]),patch('m3_root_loss_burst.bracket',return_value=dict(begin_ns=20,end_ns=21)) as restore:
            with self.assertRaises(ValueError):stop(object(),fault)
            self.assertTrue(fault['restored']);self.assertIn('0%',restore.call_args.args[-1])

    def test_inline_live_statistics_cannot_substitute_for_shutdown_footer(self):
        live='tcpdump: 16 packets captured, 16 packets received by filter, 0 packets dropped by kernel\n'
        with self.assertRaisesRegex(ValueError,'missing tcpdump counter'):validate_tcpdump_footer(live,16)
        final='16 packets captured\n16 packets received by filter\n0 packets dropped by kernel\n'
        self.assertTrue(validate_tcpdump_footer(live+final,16)['tcpdump_population_reconciled'])
