import csv,gzip,json,tempfile,hashlib,sys,platform,importlib.metadata
from pathlib import Path
from dataclasses import replace,asdict
from collections import Counter
import study as s
import ablation_core as core
import analyze_study as a
from run import burst_trace
from integrity import write_json,hashes

ROOT=Path(__file__).resolve().parent
ALPHAS=(0,.125,.25,.5,1)
def policies(calibrate=False):
    return [(f'FA{v:g}','FA',v,True) for v in ALPHAS]+([] if calibrate else [('FA0_no_drop','FA',0,False),('FA1_no_drop','FA',1,False),('EDF_safe','EDF-safe',0,True)])

def run_phase(folder,configs,seeds,calibrate=False):
    folder.mkdir();rows=[]
    with gzip.open(folder/'frames.csv.gz','wt',newline='',encoding='utf-8') as ff:
        fw=None
        for scenario,(family,c) in enumerate(configs):
            for seed in seeds:
                trace=burst_trace(c,seed) if family=='burst' else s.make_trace(c,seed)
                for label,policy,alpha,drop in policies(calibrate):
                    m,out=core.simulate(trace,c,policy,alpha,True,drop)
                    identity=dict(scenario=scenario,seed=seed,policy=label)
                    row={**identity,'family':family,'capacity':c.queue_packets,'background':c.background,'trace_sha256':trace.fingerprint(),**m}
                    # Old core uses high_fraction for class completion; explicit new names.
                    row['high_completion_fraction']=row.pop('high_fraction');row['low_completion_fraction']=row.pop('low_fraction')
                    for high,name in [(True,'high'),(False,'ordinary')]:
                        group=[f for f in out if f['high']==high]
                        for status in ('complete','expired','infeasible','overflow'):
                            g=[f for f in group if f['status']==status]
                            row[f'{name}_{status}']=len(g)
                            row[f'{name}_{status}_attempt_bytes']=sum(f['attempts'] for f in g)*c.packet_bytes
                    rows.append(row)
                    for f in out:
                        record={**identity,**f}
                        if fw is None:fw=csv.DictWriter(ff,fieldnames=list(record));fw.writeheader()
                        fw.writerow(record)
            print(folder.name,scenario,flush=True)
    a.save_csv(folder/'runs.csv',rows)
    return rows

def select(rows):
    records=[]
    for alpha in ALPHAS:
        label=f'FA{alpha:g}';gain=[];upper=[]
        for scene in range(3):
            pairs={r['seed']:r for r in rows if r['scenario']==scene and r['policy']==label}
            baseline={r['seed']:r for r in rows if r['scenario']==scene and r['policy']=='FA0'}
            loss=[baseline[k]['low_completion_fraction']-pairs[k]['low_completion_fraction'] for k in pairs]
            gain.extend(pairs[k]['weighted_fraction']-baseline[k]['weighted_fraction'] for k in pairs)
            upper.append(a.interval(loss)[2])
        records.append({'alpha':alpha,'mean_weighted_gain':sum(gain)/len(gain),'loss_ci_upper_by_background':upper,'eligible':max(upper)<=.02})
    winner=max([r for r in records if r['eligible']],key=lambda r:(r['mean_weighted_gain'],-r['alpha']))
    return {'alpha':winner['alpha'],'ordinary_loss_budget':.02,'calibration':records,'validation_seeds_unseen':list(range(5000,5030))}

def main(dest):
    dest=Path(dest).resolve()
    if dest.exists():raise FileExistsError(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.loop-pending-',dir=dest.parent))
    calibration=[('iid',s.Config(background=b)) for b in (.3,.45,.6)]
    validation=[('iid',s.Config(background=b,queue_packets=q)) for q in (40,80,160,4096) for b in (.3,.45,.6)]+[('burst',s.Config(background=.45))]
    write_json(stage/'manifest.json',{'version':'v3.2','python':sys.version,'platform':platform.platform(),'dependencies':{p:importlib.metadata.version(p) for p in ('numpy','scipy','matplotlib')},'calibration_configs':[(f,asdict(c)) for f,c in calibration],'validation_configs':[(f,asdict(c)) for f,c in validation],'calibration_seeds':list(range(4000,4020)),'validation_seeds':list(range(5000,5030)),'sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('research_loop.py','ablation_core.py','simulate.py','LOOP_PLAN.md','run.py','loop_analyze.py','review_metrics.py','REVISION_PLAN.md')}})
    chosen=select(run_phase(stage/'calibration',calibration,range(4000,4020),True))
    write_json(stage/'frozen_selection.json',chosen)
    print('Frozen alpha',chosen['alpha'],flush=True)
    run_phase(stage/'validation',validation,range(5000,5030))
    import loop_analyze
    loop_analyze.analyze(stage, output=stage)
    write_json(stage/'SHA256.json',hashes(stage));stage.rename(dest)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
