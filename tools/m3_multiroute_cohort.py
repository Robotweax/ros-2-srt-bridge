#!/usr/bin/env python3
"""Six separately owned short baseline/one-loss cases; stop on first failure."""
import argparse
import json
from pathlib import Path
from m3_network import SEEDS
from m3_source_preflight import write
from m3_ros_multiroute import run
from m3_runtime_layout import LAYOUTS


def short_cases():
    return [dict(name=('baseline' if losses==0 else 'one-loss')+'-'+str(seed),losses=losses,seed=seed,seconds=10) for losses in (0,1) for seed in SEEDS]


def thirty_second_cases():
    return [dict(name=('baseline','one-loss','two-loss')[losses]+'-'+str(seed),losses=losses,seed=seed,seconds=30) for seed in SEEDS for losses in (0,1,2)]


def execute(cases,invoke,record):
    rows=[];failed=False
    for case in cases:
        row=dict(case)
        if failed:row.update(status='not_executed',reason='preceding case failed; no retry')
        else:
            try:
                result=invoke(case)
                row.update(status=result['status'],error=result.get('error'))
                if row['status'] not in ('passed','failed'):raise ValueError('case did not return final verdict')
            except Exception as error:row.update(status='failed',error=str(error))
            failed=row['status']=='failed'
        rows.append(row);record(dict(status='failed' if failed else 'running',cases=rows,full_N3_qualification=False))
    result=dict(status='failed' if failed else 'passed',cases=rows,full_N3_qualification=False)
    record(result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--coverage',choices=('short','thirty-second'),default='short');p.add_argument('--runtime-layout',choices=tuple(LAYOUTS),default='baseline');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    def invoke(case):
        print(json.dumps(dict(event='start',**case)),flush=True)
        return run(out/case['name'],capture=True,losses=case['losses'],seed=case['seed'],seconds=case['seconds'],runtime_layout=a.runtime_layout)
    def record(value):
        write(out/'cohort.json',value)
        print(json.dumps(dict(event='progress',status=value['status'],case=value['cases'][-1])),flush=True)
    result=execute(thirty_second_cases() if a.coverage=='thirty-second' else short_cases(),invoke,record);return result['status']!='passed'


if __name__=='__main__':raise SystemExit(main())
