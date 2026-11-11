"""Existing phase/freshness/crash gates with exact current-build provenance."""
import json
from pathlib import Path
from m3_closure_assessor import (require,cleanup,assess_native_n4,assess_outage)
from m3_dds_result_timeline import common_clock
from m3_source_preflight import IMAGE
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as sample_trace
from m3_n4_sensor_check import assess as assess_freshness
from ros_adapter import check_crash
from cases import invocation


def provenance(record,freeze):
    require(freeze['schema_version']==1 and freeze['runtime_layout']['name']=='socket-disposition','wrong frozen candidate')
    require(record['runtime_layout']==freeze['runtime_layout'],'case differs from matched build')
    require(record.get('image_reference',record.get('image'))==IMAGE,'case image differs')
    require(record['source_sha256']==freeze['source_sha256'],'case source differs')
    require(record['runtime_layout']['calibration_sha256']==freeze['candidate_manifest_sha256'],'candidate manifest differs')


def assess_case(run,slot,freeze):
    invocation(slot)
    run=Path(run);report=json.loads((run/'result.json').read_text());record=json.loads((run/'provenance.json').read_text())
    provenance(record,freeze)
    require(slot['stage']=='N4' and report['status']=='passed','N4 inner harness failed')
    common_clock(report['clock_proof'])
    if 'phase' in report:proof=assess_native_n4(report,run,slot,record,freeze)
    else:
        require(report['mode']==slot.get('direction',slot.get('phase')),'ROS N4 mode differs')
        require(set(report['shutdown'])=={'operator','robot'} and all(s['passed'] for s in report['shutdown'].values()),'ROS N4 shutdown incomplete')
        if slot['id'].startswith('N4-ROS-crash-'):proof=json.loads(json.dumps(check_crash(run,slot['phase']),allow_nan=False));require(proof==report['crash'],'ROS crash audit differs')
        else:
            assess_outage(report,slot['direction'],'outage_ns','drop_readback')
            require(report['restored_ns']==max(v['bracket']['end_ns'] for v in report['outage_restore'].values()),'ROS restoration bound differs')
            load=lambda name:json.loads((run/name).read_text())
            proof=assess_freshness(source_trace(run/'robot-source.log'),load('robot-fresh-result.json'),load('operator-fresh-result.json'),sample_trace(run/'robot-bridge-0.log',allow_inactive_admissions=True),sample_trace(run/'operator-bridge-0.log'),report['outage_ns'],report['restored_ns'],slot['direction'])
            require(proof==report['freshness'],'ROS freshness audit differs')
    cleanup(run)
    return dict(status='passed',proof=proof,cleanup='recorded_owned_removal_complete')
