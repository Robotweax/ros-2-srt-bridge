"""Independent closed-capture identities for instrumented mixed-route fixtures."""
from collections import Counter
from m3_sample_trace import correlate
from m3_ros_sensor import captured, frame_key, pcap_count
from m3_packet_capture import artifact_footer


def expected_wire(events, identity, excluded=()):
    sdk=[e for e in events if e['point']==2]
    numbers=[e['message_number'] for e in sdk]
    origin=identity['initial_sequence'];binding=identity['binding']
    if sorted(numbers)!=list(range(1,len(sdk)+1)) or not sdk or any(e['initial_sequence']!=origin for e in sdk) or sum(e['kind']==4 and e['message_number']==1 for e in sdk)!=1 or any(e['kind']!=5 for e in sdk if e['message_number']!=1):
        raise ValueError('SDK/captured binding, origin or message population mismatch')
    if not set(excluded)<=set(numbers)-{1}:raise ValueError('excluded source not SDK accepted')
    keys=[((origin+e['message_number']-1)&0x7fffffff,e['message_number'],binding['socket_id'],False) for e in sdk if e['kind']==5 and e['message_number'] not in excluded]
    keys += [((origin+i)&0x7fffffff,0,binding['socket_id'],False) for i in range(3,len(sdk),4)]
    return Counter(keys)


def verify_populations(expected,native,pcap,footer):
    if expected!=native or expected!=pcap or not footer['population_reconciled']:
        raise ValueError('exact SDK/native/PCAP source/parity populations differ')


def verify_captures(path,addresses,identity,events,resume_ns,pause_ns,excluded=()):
    expected=expected_wire(events,identity,excluded);result={};binding=identity['binding']
    for role,address in addresses.items():
        status,pairs=captured(path/(role+'.mono'),address)
        if not status['ready_ns']<=resume_ns<pause_ns<=status['stop_before_ns']:raise ValueError('native capture does not cover source window')
        native=Counter(frame_key(row['prefix'],binding) for row,_ in pairs if frame_key(row['prefix'],binding) is not None)
        count,pcap=pcap_count(path/(role+'.pcap'),binding);footer=artifact_footer(path,role,count)
        verify_populations(expected,native,pcap,footer)
        result[role]=dict(status=status,footer=footer,source_records=sum(n for k,n in expected.items() if k[1]),parity_records=sum(n for k,n in expected.items() if not k[1]))
        if excluded:
            parity=((identity['initial_sequence']+7)&0x7fffffff,0,binding['socket_id'],False)
            times=[r['monotonic_ns'] for r,h in pairs if h and h['direction']==('in' if role=='operator' else 'out') and frame_key(r['prefix'],binding)==parity]
            if len(times)!=1:raise ValueError('selected parity timestamp ambiguous')
            result[role]['selected_parity_ns']=times[0]
    return result


def verify_recovery(source,local,remote,receiver,identity,parity_ns,installed_ns,remove_ns):
    """Preselected row1, last source message8; require a mixed route row and typed repair."""
    joined=correlate(local)['joined'];by_message={p['handoff']['message_number']:p for p in joined}
    row=[by_message.get(i) for i in range(5,9)]
    if any(p is None for p in row) or {p['admission']['route'] for p in row}!={1,2}:raise ValueError('preselected FEC row is not a complete mixed-route SDK row')
    target=by_message[8];a=target['admission'];h=target['handoff']
    if h['initial_sequence']!=identity['initial_sequence']:raise ValueError('selected SDK/capture origin mismatch')
    sources=[e for e in source['events'] if (e['route'],e['stamp_sec'],e['stamp_nanosec'])==(a['route'],a['stamp_sec'],a['stamp_nanosec'])]
    if len(sources)!=1:raise ValueError('selected source mapping ambiguous')
    src=sources[0];decisions=[e for e in remote['events'] if e['point']==4 and e['message_number']==8]
    if len(decisions)!=1 or decisions[0]['result']!=0:raise ValueError('selected repaired source not explicitly accepted')
    observed=[e for e in receiver['rows'] if (e['route'],e['counter'])==(src['route'],src['counter'])]
    if len(observed)!=1 or observed[0]['payload_sha256']!=src['payload_sha256']:raise ValueError('selected repaired source not observed with exact typed hash')
    if not installed_ns<=h['begin_ns'] or not a['origin_ns']<parity_ns<=decisions[0]['end_ns']<=observed[0]['observed_ns']<remove_ns:raise ValueError('repair/parity/classifier ordering mismatch')
    return dict(parity_incoming_ns=parity_ns,install_end_ns=installed_ns,remove_begin_ns=remove_ns,message_number=8,source_route=src['route'],source_counter=src['counter'],source_payload_sha256=src['payload_sha256'],row_messages=[dict(message_number=p['handoff']['message_number'],route=p['admission']['route']) for p in row],receiver_decision=decisions[0],typed_observation=observed[0],scope='SDK-accepted source selected before traffic; absent at both native/PCAP taps, accepted and typed-observed while classifier still installed; no physical-wire/cryptographic-FEC or full N3 qualification')
