"""Posthoc common-interval witness; no runtime change or unique-cause authority."""
from m3_control_fault_analysis import inside_deltas


def common_witness(window,provider_rows,identity):
    q=window['qdisc'];first=q['first'];last=q['last']
    if first is None or last is None or len(q['pairs'])==0:return dict(qualified=False,why='no paired tc snapshots')
    start=first['filter_read_ns'][1];end=last['filter_read_ns'][0]
    if start>=end:return dict(qualified=False,why='no interval between filter reads')
    # With nondecreasing counters, equal endpoint samples imply no selected PASS
    # execution throughout the interval between their read brackets under the reported cumulative-counter contract.
    packets=last['pass_counter']['packets']-first['pass_counter']['packets']
    bytes_=last['pass_counter']['bytes']-first['pass_counter']['bytes']
    if packets<0 or bytes_<0:raise ValueError('PASS counter regression')
    if not window['identity_stable']:return dict(qualified=False,why='provider identity not stable')
    if window['all_selected_source_control_observations']:return dict(qualified=False,why='other selected CONTROL hook observations')
    if packets or bytes_:return dict(qualified=False,why='PASS executions observed',pass_packets=packets,pass_bytes=bytes_)
    p=inside_deltas(provider_rows,tuple(identity),start,end)
    grew=any(p['totals'][k]>0 for k in ('data_sent','ack_sent','nak_sent'))
    return dict(qualified=bool(p['adjacent_pairs']) and grew,between_filter_read_brackets_ns=[start,end],pass_packets=packets,pass_bytes=bytes_,fully_contained_provider_pairs=len(p['adjacent_pairs']),provider=p,why=None if p['adjacent_pairs'] and grew else 'no fully contained positive selected provider increment',scope='Successful provider DATA submission or selected control accounting inside an observed counter-flat software-PASS read interval, and no selected source hook observation in the enclosing window. Aggregate port/peer selection, not per-packet identity, exact neighbor transition or unique kernel cause.')
