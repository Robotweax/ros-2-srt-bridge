import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_rtps_discovery import parse,assess,TOPICS

PREFIX='010f'+'01'*10
GUID=PREFIX+'00000103'


def packet():
    # Pinned PDML field structure: INFO_DST uses rtps.guidPrefix.dst,
    # source prefix belongs to the header, topic/GUID to a single DATA.
    return f'''<pdml creator="wireshark/4.2.2"><packet>
    <field name="frame.number" show="1"/><field name="ip.src" show="10.0.0.1"/><field name="ip.dst" show="10.0.0.2"/>
    <proto name="rtps"><field name="rtps.guidPrefix.src" value="{PREFIX}"/>
    <field name="rtps.sm.id" show="0x0e"><field name="rtps.guidPrefix.dst" value="{'02'*12}"/></field>
    <field name="rtps.sm.id" show="0x15" value="1505">
    <field name="rtps.sm.wrEntityId" show="0x000003c2"/><field name="rtps.sm.rdEntityId" show="0x000004c7"/>
    <field name="rtps.sm.seqNumber" show="1"/><field name="rtps.param.topicName" show="{TOPICS[0]}"/>
    <field name="rtps.param.endpoint_guid" value="{GUID}"/></field></proto></packet></pdml>'''


class PdmlTests(unittest.TestCase):
    def read(self,text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_text(text);return parse(p)

    def test_destination_context_and_submessage_scope(self):
        r=self.read(packet());row=r['rows'][0]
        self.assertEqual(row['writer'],PREFIX+'000003c2');self.assertEqual(row['destination_prefix'],'02'*12)
        self.assertEqual(row['topic'],TOPICS[0]);self.assertEqual(row['endpoint'],GUID)
        # A second DATA must not inherit the first DATA's topic or endpoint.
        tree=E.fromstring(packet());sm=copy.deepcopy(tree.find(".//field[@name='rtps.sm.id'][@show='0x15']"))
        for f in list(sm):
            if f.get('name') in ('rtps.param.topicName','rtps.param.endpoint_guid'):sm.remove(f)
        tree.find('.//proto').append(sm)
        rows=self.read(E.tostring(tree,encoding='unicode'))['rows'];self.assertIsNone(rows[1]['topic']);self.assertIsNone(rows[1]['endpoint'])


    def test_heartbeat_range_is_never_a_data_sample_sequence(self):
        text=packet().replace('show="0x15"','show="0x07"').replace('<field name="rtps.sm.seqNumber" show="1"/>','<field name="rtps.sm.seqNumber" show="1"/><field name="rtps.sm.seqNumber" show="4"/>')
        r=self.read(text);self.assertIsNone(r['rows'][0]['sequence'])

    def test_untrusted_schema_malformed_truncation_and_budget_are_rejected(self):
        for text in (packet().replace('wireshark/4.2.2','wireshark/9'),packet()[:-4],packet().replace('</packet>','<proto name="_ws.malformed"/></packet>'),packet().replace(PREFIX, 'ab',1)):
            with self.subTest(text=text[-40:]),self.assertRaises((ValueError,E.ParseError)):self.read(text)
        with patch('m3_rtps_discovery.MAX_RECORDS',0),self.assertRaisesRegex(ValueError,'budget'):self.read(packet())
        with patch('m3_rtps_discovery.MAX_BYTES',1),self.assertRaisesRegex(ValueError,'budget'):self.read(packet())

    def test_first_ipv4_fragment_uses_pinned_boolean_show_value(self):
        text=packet().replace('<proto name="rtps">','<field name="ip.frag_offset" show="0"/><field name="ip.flags.mf" show="True"/><proto name="rtps">')
        result=self.read(text);self.assertEqual(result['fragment_frames'],1)

    def test_ambiguous_field_and_source_context_are_withheld(self):
        text=packet().replace('<field name="rtps.sm.seqNumber" show="1"/>','<field name="rtps.sm.seqNumber" show="1"/><field name="rtps.sm.seqNumber" show="2"/>')
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.read(text)
        with self.assertRaisesRegex(ValueError,'INFO_SRC'):self.read(packet().replace('show="0x0e"','show="0x0c"'))


class BindingTests(unittest.TestCase):
    def fixture(self):
        ad=dict(source='10.0.0.1',destination='10.0.0.2',source_prefix=PREFIX,kind=0x15,writer=PREFIX+'000003c2',sequence=1,topic=TOPICS[0],endpoint=GUID,submessage_sha256='ab'*32)
        data=dict(ad,writer=GUID,sequence=9,topic=None,endpoint=None)
        return dict(operator=dict(rows=[ad,data]),robot=dict(rows=[copy.deepcopy(ad),copy.deepcopy(data)])),dict(operator='10.0.0.1',robot='10.0.0.2')

    def test_binding_is_writer_guid_not_a_topic_string_anywhere_in_packet(self):
        decoded,addresses=self.fixture();r=assess(decoded,addresses)
        self.assertEqual(r['topics'][TOPICS[0]]['data']['robot']['by_direction'],dict(peer_source=1))
        decoded['robot']['rows'][1]['writer']='ff'*16
        r=assess(decoded,addresses);self.assertEqual(r['topics'][TOPICS[0]]['data']['robot']['observations'],0)
        self.assertEqual(r['unbound_data_submessages']['robot'],2)

    def test_known_missing_advertisement_never_invents_local_receipt(self):
        decoded,addresses=self.fixture();decoded['robot']['rows'].pop(0)
        r=assess(decoded,addresses)
        self.assertEqual(r['topics'][TOPICS[0]]['advertisements']['robot']['observations'],0)
        presence=r['cross_capture_advertisement_presence']['operator']
        self.assertEqual(presence['present_both'],0);self.assertEqual(len(presence['source_only']),1)
        # Union directory can still label the observed DATA, but is explicitly
        # retrospective and cannot claim this peer processed the discovery.
        self.assertEqual(r['topics'][TOPICS[0]]['data']['robot']['observations'],1)
        decoded['operator']['rows'].pop(0)
        r=assess(decoded,addresses);self.assertEqual(r['binding_count'],0)
        self.assertIsNone(r['topics'][TOPICS[0]]['data']['robot']['observations'])
        self.assertFalse(r['topics'][TOPICS[0]]['data']['robot']['publication_binding_available'])

    def test_conflicting_or_relayed_endpoint_identity_is_rejected(self):
        decoded,addresses=self.fixture();bad=copy.deepcopy(decoded['robot']['rows'][0]);bad['topic']=TOPICS[1];decoded['robot']['rows'].append(bad)
        with self.assertRaisesRegex(ValueError,'ambiguous'):assess(decoded,addresses)
        decoded,addresses=self.fixture();decoded['robot']['rows'][0]['endpoint']='ff'*16
        with self.assertRaisesRegex(ValueError,'participant'):assess(decoded,addresses)
