from pathlib import Path
import copy,hashlib,json,socket,struct,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_arp_reply_observer import selector,reply_words,parse_tc_json,counters
from m3_arp_reply_analysis import phase_gate,frame_key,pcap_keys,selected_key
from m3_tap_probe import MAGIC

SOURCE='10.0.0.3';TARGET='10.0.0.2';SM='02:00:00:00:00:03';TM='02:00:00:00:00:02'


def rule(verdict='drop'):
    actions=[dict(order=i,index=i,kind='gact',control_action=dict(type=k),stats=dict(packets=2,bytes=84,drops=2 if k=='drop' else 0)) for i,k in enumerate(('pipe',verdict),1)]
    return [dict(kind='u32',protocol='arp',options=dict(not_in_hw=True,_repeated_match=[dict(value=format(v,'x'),mask='ffffffff',off=k,offmask='') for k,v in reply_words(SOURCE,TARGET,SM,TM).items()],actions=actions))]


def phase(fault=True):
    case=2;origin=1_000_000_000;end=origin+1_350_000_000;remove=dict(begin_ns=end,end_ns=end+100)
    count=dict(eligible=dict(packets=2,bytes=84,drops=0),verdict=dict(packets=2,bytes=84,drops=2 if fault else 0),verdict_type='drop' if fault else 'pass')
    c=dict(status='passed',removal=remove,snapshots=[dict(counters=copy.deepcopy(count)),dict(counters=count)])
    sent=dict(case=case,count=3,rows=[dict(sequence=n,before_ns=origin+n,after_ns=origin+n+1) for n in range(3)])
    t=end+10000 if fault else origin+10000;rows=[]
    for n in range(3):
        payload=MAGIC+struct.pack('!II',case,n)+bytes(1184);rows.append(dict(case=case,sequence=n,monotonic_ns=t+n,sha256=hashlib.sha256(payload).hexdigest()))
    payload=MAGIC+struct.pack('!II',case+1000,0)+bytes(1184);rows.append(dict(case=case+1000,sequence=0,monotonic_ns=end+20000,sha256=hashlib.sha256(payload).hexdigest()))
    received=dict(complete=True,rows=rows);native={}
    for role in ('operator','robot'):
        events=[dict(probe=(r['case'],r['sequence']),monotonic_ns=r['monotonic_ns']) for r in rows]
        for i in range(1 if fault else 2):events.append(dict(monotonic_ns=t-10+i,arp=dict(identity_class='outgoing_local_reply' if role=='robot' else 'incoming_peer_reply')))
        native[role]=events
    return case,fault,dict(end_ns=100),c,sent,received,native


class ArpReplyObserverTests(unittest.TestCase):
    def test_exact_payload_has_reply_opcode_and_both_owned_mac_ip_pairs(self):
        words=reply_words(SOURCE,TARGET,SM,TM);payload=b''.join(v.to_bytes(4,'big') for v in words.values())
        self.assertEqual(payload[:8],bytes.fromhex('0001080006040002'));self.assertEqual(payload[8:14].hex(':'),SM);self.assertEqual(payload[24:28],socket.inet_aton(TARGET))
        argv=selector(SOURCE,TARGET,SM,TM,'drop');self.assertEqual(argv[-6:],['action','gact','pipe','action','gact','drop']);self.assertIn('skip_hw',argv)
        with self.assertRaises(ValueError):selector(SOURCE,SOURCE,SM,TM,'drop')
    def test_all_repeated_tc_match_keys_are_preserved_not_only_last_word(self):
        text='{"options":{"match":{"off":0},"success":0,"match":{"off":4},"success":0}}'
        r=parse_tc_json(text);self.assertEqual([v['off'] for v in r['options']['_repeated_match']],[0,4])
        with self.assertRaisesRegex(ValueError,'duplicate'):parse_tc_json('{"actions":[],"actions":[]}')
    def test_wrong_request_or_partial_selector_rejected(self):
        for mutate in (lambda r:r[0]['options']['_repeated_match'][1].update(value='6040001'),lambda r:r[0]['options']['_repeated_match'].pop(),lambda r:r[0]['options'].update(not_in_hw=False)):
            r=rule();mutate(r)
            with self.assertRaises(ValueError):counters(r,SOURCE,TARGET,SM,TM,'drop')
    def test_pipe_must_not_be_terminal_pass_or_share_action_index(self):
        for mutate in (lambda a:a[0]['control_action'].update(type='pass'),lambda a:a[1].update(index=1),lambda a:a[0]['stats'].update(drops=1)):
            r=rule();mutate(r[0]['options']['actions'])
            with self.assertRaises(ValueError):counters(r,SOURCE,TARGET,SM,TM,'drop')
        self.assertEqual(counters(rule(),SOURCE,TARGET,SM,TM,'drop')['eligible']['packets'],2)


class ArpReplyPhaseTests(unittest.TestCase):
    def test_clean_and_drop_restore_controls_with_distinct_fresh_datagram(self):
        for fault in (False,True):
            r=phase_gate(*phase(fault));self.assertEqual(r['original_udp_delivered_once'],3);self.assertEqual(r['dropped_replies'],2 if fault else 0)
    def test_generated_counter_zero_or_unequal_verdict_not_proof(self):
        for key,value in [('packets',0),('bytes',80),('drops',0)]:
            args=list(phase());args[3]['snapshots'][-1]['counters']['verdict'][key]=value
            with self.assertRaisesRegex(ValueError,'counter'):phase_gate(*args)
    def test_reply_or_udp_during_fault_rejected(self):
        for event in [dict(monotonic_ns=2_000_000_000,arp=dict(identity_class='outgoing_local_reply')),dict(monotonic_ns=2_000_000_000,probe=(2,0))]:
            args=list(phase());args[-1]['robot'].append(event)
            with self.assertRaises(ValueError):phase_gate(*args)
    def test_reflected_arp_cannot_replace_genuine_restored_reply(self):
        args=list(phase());args[-1]['operator'][-1]['arp']['identity_class']='reflected_local_reply'
        with self.assertRaisesRegex(ValueError,'genuine'):phase_gate(*args)
    def test_repeated_udp_or_changed_payload_or_late_removal_rejected(self):
        args=list(phase());args[5]['rows'].append(copy.deepcopy(args[5]['rows'][0]))
        with self.assertRaisesRegex(ValueError,'population'):phase_gate(*args)
        args=list(phase());args[5]['rows'][0]['sha256']='00'
        with self.assertRaisesRegex(ValueError,'payload'):phase_gate(*args)
        args=list(phase());args[3]['removal']['end_ns']=4_000_000_000
        with self.assertRaisesRegex(ValueError,'timing'):phase_gate(*args)
    def test_probe_packet_shape_and_truncated_pcap_are_not_rescued(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a';p.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+b'bad')
            with self.assertRaisesRegex(ValueError,'record'):pcap_keys(p)
        with self.assertRaises(ValueError):frame_key(b'short',5)


class ArpReplyScopeTests(unittest.TestCase):
    def test_gratuitous_arp_is_retained_background_not_cross_peer_exchange(self):
        addresses=dict(operator=TARGET,robot=SOURCE)
        key=('arp',42,1,SM,'ff:ff:ff:ff:ff:ff',SM,SOURCE,'00:00:00:00:00:00',TARGET)
        self.assertTrue(selected_key(key,addresses))
        self.assertFalse(selected_key(key[:8]+(SOURCE,),addresses))
        self.assertTrue(selected_key(('udp',1242,2,0),addresses))
        self.assertFalse(selected_key(key[:2]+(3,)+key[3:],addresses))
