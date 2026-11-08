from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_rtps_partial import inspect
from test_m3_rtps_discovery import packet


class PartialTests(unittest.TestCase):
    def read(self,text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_text(text);return inspect(p)

    def test_truncated_body_never_becomes_complete_advertisement(self):
        text=packet().replace('<proto name="rtps">','<field name="ip.frag_offset" show="0"/><field name="ip.flags.mf" show="True"/><proto name="_ws.malformed"/><proto name="rtps">')
        result=self.read(text);self.assertEqual(len(result['rows']),1);self.assertFalse(result['rows'][0]['complete_advertisement'])
        self.assertIsNotNone(result['rows'][0]['partial_topic'])
        self.assertNotIn('endpoint',result['rows'][0])

    def test_full_or_continuation_datagrams_do_not_qualify_as_this_selection(self):
        for offset,mf in [('185','True'),('0','False')]:
            text=packet().replace('<proto name="rtps">',f'<field name="ip.frag_offset" show="{offset}"/><field name="ip.flags.mf" show="{mf}"/><proto name="rtps">')
            with self.subTest(offset=offset,mf=mf),self.assertRaises(ValueError):self.read(text)
