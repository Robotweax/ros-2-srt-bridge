import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_loaded_start_analysis import join_attempt


class LoadedStartTests(unittest.TestCase):
    def setUp(self):
        self.a=dict(route=100,payload_hash='hash',session='session',source_epoch='operator',source_ns=100,owner_epoch='operator',state=4,reason=0,deadline_ns=1100,dispatched_ns=0)
        self.b=dict(self.a,owner_epoch='robot',deadline_ns=1000,dispatched_ns=200)
        self.entry=dict(number=1,terminal=4,sdk_handoffs=1,sender=self.a,receiver=self.b)
        self.group=dict(identity=dict(request=(1).to_bytes(16,'little').hex(),session='session',route=100,origin_ns=100,owner_epoch='robot'),branch='worker_handler_invoked',events=[dict(point=43,entry_owner_epoch='robot',command_deadline_ns=1000,terminal_state=4,terminal_reason=0,consume_ns=600,consume_deadline_ns=700,grant_deadline_ns=700,second_gate_checked=True,second_gate_ns=610,second_gate_deadline_ns=700)])
    def test_exact_actual_slack_and_no_admission_substitution(self):
        r=join_attempt(self.entry,[self.group],[]);self.assertEqual(r['actual_slack_ns'],dict(consume=100,second_gate=90,command_budget_at_consume=400,command_minus_grant=300));self.assertIsNone(r['last_admission_clock_margin_ns'])
    def test_missing_start_is_not_nondispatch_proof(self):
        with self.assertRaisesRegex(ValueError,'dispatched record'):join_attempt(self.entry,[],[])
        self.b['dispatched_ns']=0;r=join_attempt(self.entry,[],[]);self.assertIsNone(r['start']);self.assertIn('not nonexecution proof',r['unavailable_reason'])
    def test_wrong_owner_deadline_and_terminal_are_refused(self):
        for changes in (dict(entry_owner_epoch='other'),dict(command_deadline_ns=1001),dict(terminal_state=6)):
            g=copy.deepcopy(self.group);g['events'][0].update(changes)
            with self.assertRaises(ValueError):join_attempt(self.entry,[g],[])
        with self.assertRaisesRegex(ValueError,'multiple'):join_attempt(self.entry,[self.group,self.group],[])
    def test_query_or_foreign_admission_cannot_set_old_clock_margin(self):
        adm=dict(session='wrong',route=100,origin_ns=100,evaluated_ns=110,clock_deadline_ns=111)
        with self.assertRaisesRegex(ValueError,'admission/journal'):join_attempt(self.entry,[self.group],[adm])


if __name__=='__main__':unittest.main()
