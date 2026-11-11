"""Exact window deltas at stable, source-paused, empty-pipeline checkpoints.

Pipeline totals cover both routes. Per-route publication histograms are separate.
Wire gap means SRT acceptance -> decoded receiver SAMPLE, not proven packet loss.
"""
import math


def summarize_window(begin, end, interval):
    def delta(role,key):
        result=end[role][key]-begin[role][key]
        if result<0:raise ValueError('counter reset/regression: '+role+'/'+key)
        return int(result)
    for role in ('sender','receiver'):
        if len(begin[role]['owner_epoch'])!=16 or not any(begin[role]['owner_epoch']) or begin[role]['owner_epoch']!=end[role]['owner_epoch']:
            raise ValueError('owner restarted or epoch missing: '+role)
    for checkpoint in (begin,end):
        for role in ('sender','receiver'):
            for key in ('sensor_ingress_pending','sensor_outbound_pending','sensor_receive_pending'):
                if checkpoint[role][key]:raise ValueError('checkpoint has pending samples')
    s=lambda key:delta('sender',key)
    r=lambda key:delta('receiver',key)
    source=delta('device','imu_published')+delta('device','joints_published')
    observed=delta('observer','imu')+delta('observer','joints')
    losses=dict(upstream_dds=source-s('samples_ingress'),
        validation=s('invalid_samples')+s('oversize_samples'),admission=s('context_drops'),
        ingress_replaced=s('sensor_ingress_replaced'),ingress_flushed=s('sensor_ingress_flushed'),
        input_rejected=s('sensor_input_rejected'),outbound_replaced=s('sensor_outbound_replaced'),
        outbound_expired=s('sensor_outbound_expired'),outbound_flushed=s('sensor_outbound_flushed'),
        srt_accept_to_receiver_gap=s('sensor_sent')-r('transport_samples_received'),
        receiver_rejected=r('transport_samples_rejected'),receive_replaced=r('sensor_receive_replaced'),
        receive_flushed=r('sensor_receive_flushed'),poll_expired=r('sensor_poll_expired'),
        publication_rejected=r('invalid_samples')+r('stale_samples')+r('context_drops'),
        observer_dds=r('samples_published')-observed)
    if any(value<0 for value in losses.values()):raise ValueError('negative loss attribution; checkpoints did not align')
    balances=dict(typed_ingress=s('samples_ingress')-s('sensor_submitted')-losses['validation']-losses['admission'],
        ingress_mailbox=s('sensor_submitted')-s('sensor_inputs')-losses['ingress_replaced']-losses['ingress_flushed'],
        outbound_queue=s('sensor_inputs')-losses['input_rejected']-s('sensor_sent')-losses['outbound_replaced']-losses['outbound_expired']-losses['outbound_flushed'],
        receive_mailbox=r('transport_samples_received')-losses['receiver_rejected']-r('sensor_polled')-losses['receive_replaced']-losses['receive_flushed']-losses['poll_expired'],
        publication=r('sensor_polled')-r('samples_published')-losses['publication_rejected'],
        end_to_end=source-observed-sum(losses.values()))
    if any(balances.values()):raise ValueError('pipeline accounting does not balance: '+str(balances))
    histograms={}
    for route in ('imu','joint'):
        key=route+'_age_upper_histogram_ms'
        if len(begin['receiver'][key])!=251 or len(end['receiver'][key])!=251:raise ValueError('invalid histogram length')
        values=[int(b)-int(a) for a,b in zip(begin['receiver'][key],end['receiver'][key])]
        if len(values)!=251 or any(v<0 for v in values):raise ValueError('invalid histogram delta')
        count=sum(values);row=dict(count=count,rounding='up to 1ms',maximum_ms=None)
        for label,fraction in [('p50_ms',.5),('p95_ms',.95),('p99_ms',.99),('maximum_ms',1)]:
            rank=math.ceil(count*fraction);total=0;row[label]=None
            for i,value in enumerate(values):
                total+=value
                if count and total>=rank:row[label]=i;break
        histograms[route]=row
    if sum(row['count'] for row in histograms.values())!=r('samples_published'):raise ValueError('window histogram population mismatch')
    seconds=(interval['pause_monotonic_ns']-interval['resume_monotonic_ns'])/1e9
    if seconds<=0:raise ValueError('invalid publication interval')
    return dict(source_produced=source,observer_received=observed,missing=source-observed,losses=losses,
        balances=balances,source_enabled_seconds=seconds,
        source_actual_hz=dict(imu=delta('device','imu_published')/seconds,joints=delta('device','joints_published')/seconds),
        published=r('samples_published'),age_upper_histograms=histograms,
        scope='source-fenced and drained checkpoint deltas; no startup/diagnostic tail; SRT gap is not automatically WAN loss')
