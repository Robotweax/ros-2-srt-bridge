import copy
import json
import subprocess
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_control_fault import selector,counters,start,stop


def filters():
    return [dict(pref=49152,kind='u32',protocol='ip',options=dict(actions=[dict(kind='gact',control_action=dict(type='drop'),stats=dict(packets=8,drops=8,bytes=400))]))]


class Lab:
    containers={'operator':'owned-operator','robot':'owned-robot'}
    addresses={'operator':'10.0.0.1','robot':'10.0.0.2'}
    def __init__(self):self.calls=[];self.present=False
    def inside(self,role,label,argv):
        self.calls.append((role,label,argv))
        if label=='control-fault-qdisc-before':return '[]'
        if label=='control-fault-hook':return ''
        if label in ('control-fault-install','control-fault-remove','control-fault-abort-remove'):
            self.present=label.endswith('install')
            return json.dumps(dict(begin_ns=10 if self.present else 100,end_ns=20 if self.present else 110,exit_code=0))
        return json.dumps(filters() if self.present else [])


class FaultTests(unittest.TestCase):
    def test_exact_control_direction_and_peer(self):
        for role,port in [('operator','sport'),('robot','dport')]:
            args=selector(role,'10.0.0.2')
            self.assertIn(port,args);self.assertIn('10.0.0.2/32',args)
            self.assertEqual(args[-2:],['action','drop']);self.assertNotIn('10081',args)
        for role,peer in [('bad','10.0.0.2'),('robot','127.0.0.1'),('robot','::1'),('robot','0.0.0.0')]:
            with self.assertRaises(ValueError):selector(role,peer)

    def test_drop_readback_requires_single_matching_action(self):
        self.assertEqual(counters(filters())['drops'],8)
        for mutate in ('action','pref','stats','multiple','zero'):
            data=filters()
            if mutate=='action':data[0]['options']['actions'][0]['control_action']['type']='pass'
            if mutate=='pref':data[0]['pref']=1
            if mutate=='stats':data[0]['options']['actions'][0]['stats']['drops']=7
            if mutate=='multiple':data+=copy.deepcopy(data)
            if mutate=='zero':data=[]
            with self.assertRaises(ValueError):counters(data)

    def test_install_remove_and_vm_brackets_only_owned_roles(self):
        lab=Lab();fault=start(lab,'operator');self.assertFalse(fault['restored'])
        stop(lab,fault);self.assertTrue(fault['restored'])
        self.assertEqual(fault['guaranteed_active_ns'],[20,100])
        self.assertTrue(all(role=='operator' for role,_,_ in lab.calls))
        with self.assertRaises(ValueError):start(lab,'unknown')

    def test_runner_rejects_fault_without_required_diagnostics_before_start(self):
        root=Path(__file__).resolve().parents[1]
        for extra in ([],['--profile','N5']):
            p=subprocess.run([sys.executable,str(root/'tools/run_m3.py'),'--control-egress-fault','operator','--seconds','45']+extra,capture_output=True,text=True)
            self.assertEqual(p.returncode,2)
            self.assertIn('CONTROL fault requires',p.stderr)

    def test_captured_preference_scoped_readback_omits_pref(self):
        path=Path(__file__).resolve().parents[1]/'evidence/m3-control-egress-fault-2026-11-06/failed-run/control-fault-filter-installed.log'
        self.assertEqual(counters(json.loads(path.read_text())),dict(packets=0,drops=0,bytes=0))

    def test_bad_install_readback_removes_filter_before_raising(self):
        class BadLab(Lab):
            def inside(self,role,label,argv):
                result=super().inside(role,label,argv)
                return '[]' if label=='control-fault-filter-installed' else result
        lab=BadLab()
        with self.assertRaises(ValueError):start(lab,'operator')
        self.assertFalse(lab.present)
        self.assertIn('control-fault-abort-remove',[label for _,label,_ in lab.calls])

    def test_bad_final_readback_still_removes_filter(self):
        class BadFinalLab(Lab):
            def inside(self,role,label,argv):
                result=super().inside(role,label,argv)
                return '[]' if label=='control-fault-filter-final' else result
        lab=BadFinalLab();fault=start(lab,'operator')
        with self.assertRaises(ValueError):stop(lab,fault)
        self.assertTrue(fault['restored'])
        self.assertFalse(lab.present)
