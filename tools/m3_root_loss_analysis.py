#!/usr/bin/env python3
"""Known child-loss settled-window signature; not full N4 or historical cause proof."""
import argparse,json
from pathlib import Path
from m3_dds_result_timeline import common_clock
from m3_control_liveness import digest,parse_control
from m3_monotonic_capture import records
from m3_qdisc_diagnostics import summarize
from m3_qdisc_gap_analysis import inside_deltas


def settled_window(fault):
    if not fault.get('restored'):raise ValueError('root burst not restored')
    start=fault['install']['end_ns']+500000000;end=fault['remove']['begin_ns']-100000000
    if end-start<1000000000:raise ValueError('insufficient settled loss interval')
    return start,end


def analyze(run,flow):
    d=json.loads((run/'run.json').read_text());proof=common_clock(d['clock_namespace_proof'])
    if d['status']=='running' or proof!=flow['clock_proof']:raise ValueError('requires closed clock-associated run')
    fault=d['root_loss_burst'];start,end=settled_window(fault);role=fault['role'];peer='robot' if role=='operator' else 'operator'
    path=run/(role+'-qdisc-samples.jsonl');summary=summarize(path);before=digest(path);rows=[json.loads(line) for line in path.read_text().splitlines()];delta=inside_deltas(rows,start,end)
    if digest(path)!=before:raise ValueError('counter file changed')
    addresses=json.loads((run/'network.json').read_text())['addresses'];counts={}
    for side in (role,peer):
        p=run/(side+'.mono');sha=digest(p)
        if sha!=flow['native_sha256'][side]:raise ValueError('primary native hash mismatch')
        status=d['monotonic_captures']['statuses'][side]
        if not status['ready_ns']<=start<end<fault['remove']['end_ns']+3000000000<=status['stop_before_ns']:raise ValueError('native interval coverage')
        during=restored=0
        for row in records(p):
            t=row['monotonic_ns']
            if not (start<t<end or fault['remove']['end_ns']<=t<fault['remove']['end_ns']+3000000000):continue
            value=parse_control(row,addresses[side],status['mtu'])
            if value and value['direction']=='out':
                during+=start<t<end;restored+=fault['remove']['end_ns']<=t<fault['remove']['end_ns']+3000000000
        if digest(p)!=sha:raise ValueError('native file changed')
        counts[side]=dict(outgoing_control_in_settled_window=during,outgoing_control_after_restore=restored)
    observed=bool(delta['pairs'] and delta['totals']['pass_packets']>0 and delta['totals']['root_drops']>0 and counts[role]['outgoing_control_in_settled_window']==0 and all(c['outgoing_control_after_restore']>0 for c in counts.values()))
    return dict(known_child_loss_signature_observed=observed,fault=fault,settled_ns=[start,end],qdisc=delta,captures=counts,qdisc_samples_sha256=before,observer_summary=summary,original_PCAP_population_reconciled=d['pcap_population_reconciled'],scope='known configured whole-endpoint child loss, counter pairs inside predeclared settled interval; root counts whole interface, no exact per-packet identity/loss or physical delivery; not N4 command-phase/historical qualification; no PCAP gate rescue')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--flow',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=analyze(a.run,json.loads(a.flow.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n')
    if not r['known_child_loss_signature_observed']:raise SystemExit('known settled signature not observed; retain result')
