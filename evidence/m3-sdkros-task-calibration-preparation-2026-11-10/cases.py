"""One SDK/ROS calibration grammar; no campaign ID is enabled."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SLOT=dict(id='SDKROS-calibration-N0-1701-10s',stage='calibration_only',profile='N0',seed=1701,source_seconds=10,runtime_layout='socket-disposition')
def cases():return [dict(SLOT)]
def allowed(profile,seed,seconds):return (profile,seed,seconds)==('N0',1701,10)
def disabled_ids():return [r['id'] for r in json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']]
def enabled_ids():return []
def authorize(value,digest):raise ValueError('campaign grants refused; separate SDKROS calibration grant required')
