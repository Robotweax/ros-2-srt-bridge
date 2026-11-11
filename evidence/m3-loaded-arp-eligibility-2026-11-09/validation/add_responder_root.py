from pathlib import Path
p=Path('tools/m3_loaded_arp_analysis.py');s=p.read_text().replace('from m3_monotonic_capture import records','from m3_monotonic_capture import records\nfrom m3_qdisc_diagnostics import summarize as qdisc_summary\nfrom m3_qdisc_gap_analysis import inside_deltas')
at=s.index('\ndef analyze(run,manifest):')
s=s[:at]+'''
def root_comparison(qdisc_rows,role,window,envelope):
    # ARP responder is opposite the CONTROL requester. Never attach the
    # requester's root drops to an emitted reply from the other peer.
    rows=qdisc_rows[role]
    return dict(role=role,within_control_window=inside_deltas(rows,*window),within_reply_read_envelope=None if envelope is None else inside_deltas(rows,*envelope),scope='Reply-source whole-interface root snapshots; contained read pairs only, different tails from reply counters; no per-ARP drop attribution or mirrored-child sum.')

''' + s[at:]
s=s.replace("summaries={};rows={};hashes={};arps=", "summaries={};rows={};hashes={};qdisc_rows={};arps=")
s=s.replace("for f in (p,q):", "qr=run/(role+'-qdisc-samples.jsonl');qs=qr.with_suffix('.status.json')\n        for f in (p,q,qr,qs):")
s=s.replace("summaries[role]=summarize(p);rows[role]=", "qdisc_summary(qr);qdisc_rows[role]=[json.loads(l) for l in qr.read_text().splitlines()]\n        summaries[role]=summarize(p);rows[role]=")
s=s.replace("comparisons[role]=dict(reads=v,witness=reply_witness(v,source,sink),", "comparisons[role]=dict(reads=v,witness=reply_witness(v,source,sink),reply_source_root=root_comparison(qdisc_rows,role,[start,end],v['outer_read_envelope_ns']),")
p.write_text(s)
p=Path('tests/test_m3_loaded_arp.py');s=p.read_text().replace('interval,reply_witness','interval,reply_witness,root_comparison');s+='''

class ReplyRootScopeTests(unittest.TestCase):
    def roots(self,multiplier):
        return [dict(begin_ns=n*100,end_ns=n*100+10,pass_counter=dict(packets=n,bytes=n*10),root=dict(packets=n,bytes=n*10,drops=n*multiplier,overlimits=n,backlog=n,qlen=n)) for n in range(1,5)]
    def test_reply_source_role_not_requester_root_is_used(self):
        rows=dict(operator=self.roots(3),robot=self.roots(7))
        r=root_comparison(rows,'robot',[90,420],[150,350])
        self.assertEqual(r['role'],'robot');self.assertEqual(r['within_control_window']['totals']['root_drops'],21)
        self.assertEqual(r['within_reply_read_envelope']['totals']['root_drops'],7)
    def test_missing_envelope_is_not_zero_root_loss(self):
        r=root_comparison(dict(operator=self.roots(3)),'operator',[90,420],None)
        self.assertIsNone(r['within_reply_read_envelope'])
''';p.write_text(s)
