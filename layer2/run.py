"""Finite, paired experiments; publish only after validation and audit succeed."""
import argparse, csv, gzip, hashlib, json, os, platform, sys, tempfile
from pathlib import Path
from dataclasses import asdict, replace
import study as s
import analyze_study as a
from integrity import hashes, write_json

ROOT=Path(__file__).resolve().parent
POLICIES=[('FIFO',0),('EDF',0),('EDF-safe',0),('FA',0),('FA',1)]

def burst_trace(config,seed):
    trace=s.make_trace(config,seed)
    # Stationary two-state Markov attempt-success process. Mean failure p,
    # autocorrelation rho=0.9; unrelated extra RNG stream preserves frame/background inputs.
    rng=s.np.random.default_rng(s.np.random.SeedSequence([seed,3003]))
    p=config.loss;rho=.9
    bad=bool(rng.random()<p)
    success=s.np.empty(len(trace.success),bool)
    for t in range(len(success)):
        success[t]=not bad
        bad=bool(rng.random() < (p+rho*(1-p) if bad else p*(1-rho)))
    success.flags.writeable=False
    return replace(trace,success=success)

def settings(suite):
    if suite=='full':return list(s.scenarios())
    base=s.Config(background=.45)
    return [('main',base,POLICIES),('buffer',replace(base,queue_packets=40),POLICIES),('burst',base,POLICIES)]

def run(output,suite,seed_start,nseeds):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Output exists; select a new --output directory')
    if nseeds<2 or seed_start<0:raise ValueError('At least two seeds, nonnegative seed start required')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'-pending-',dir=output.parent))
    try:
        validation=s.validate()
        configs=settings(suite);seeds=list(range(seed_start,seed_start+nseeds))
        sources=['simulate.py','study.py','analyze_study.py','run.py','integrity.py','EXPERIMENT_PLAN.md']
        manifest={'schema_version':3,'seeds':seeds,'suite':suite,'python':sys.version,'platform':platform.platform(),
                  'numpy':s.np.__version__,'ordinary_floor':.70,'burst_rho':.9,
                  'scenarios':[{'family':family,'config':asdict(c),'policies':pol} for family,c,pol in configs],
                  'sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}}
        write_json(stage/'manifest.json',manifest)
        with (stage/'runs.csv').open('w',newline='',encoding='utf-8') as rf, gzip.open(stage/'frames.csv.gz','wt',newline='',encoding='utf-8') as ff, (stage/'sources.csv').open('w',newline='',encoding='utf-8') as sf:
            rw=fw=sw=None
            for scenario,(family,c,policies) in enumerate(configs):
                for seed in seeds:
                    trace=burst_trace(c,seed) if family=='burst' else s.make_trace(c,seed)
                    for policy,alpha in policies:
                        metrics,outcomes=s.checked_simulate(trace,c,policy,alpha)
                        identity=dict(scenario=scenario,seed=seed,policy=policy,alpha=alpha)
                        rates=[]
                        for source in range(c.sources):
                            frames=[f for f in outcomes if f['source']==source]
                            completed=sum(f['status']=='complete' for f in frames)
                            rate=completed/len(frames) if frames else float('nan')
                            rates.append(rate)
                            row={**identity,'source':source,'generated':len(frames),'completed':completed,'complete_fraction':rate}
                            if sw is None:sw=csv.DictWriter(sf,fieldnames=list(row));sw.writeheader()
                            sw.writerow(row)
                        metrics.update(source_min_completion=min(rates),source_completion_gap=max(rates)-min(rates),
                            ordinary_floor_breached=int(metrics['low_completion_fraction']<.70),
                            overflow_high_frames=sum(f['status']=='overflow' and f['high'] for f in outcomes))
                        row={**identity,'family':family,'trace_sha256':trace.fingerprint(),**{'cfg_'+k:v for k,v in asdict(c).items()},**metrics}
                        if rw is None:rw=csv.DictWriter(rf,fieldnames=list(row));rw.writeheader()
                        rw.writerow(row)
                        for f in outcomes:
                            row={**identity,**f}
                            if fw is None:fw=csv.DictWriter(ff,fieldnames=list(row));fw.writeheader()
                            fw.writerow(row)
                print(f'Completed scenario {scenario+1}/{len(configs)}',flush=True)
        a.OUT=stage;a.PROJECT=ROOT
        rows=a.load_rows();audit=a.audit(rows);a.summarize(rows)
        # Additional baseline contrast, clearly exploratory; reuse same paired estimator.
        contrast=[]
        for r in rows:
            if (r['policy'],r['alpha']) in [('EDF-safe',0),('FA',1)]:
                contrast.append({**r,'policy':'FA','alpha':0 if r['policy']=='EDF-safe' else 1,'family':'exploratory'})
        contrast_dir=stage/'edf_safe_comparison';contrast_dir.mkdir();a.OUT=contrast_dir;a.summarize(contrast);a.OUT=stage
        write_json(stage/'audit.json',audit);write_json(stage/'validation.json',validation)
        write_json(stage/'SHA256.json',hashes(stage))
        # No overwrite publication, same filesystem, pending output never presented as complete.
        if output.exists():raise FileExistsError(output)
        stage.rename(output)
        print('Published '+str(output),flush=True)
    except BaseException:
        print('Not published; diagnostic staging directory: '+str(stage),file=sys.stderr)
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--suite',choices=['smoke','stress','full'],default='smoke')
    p.add_argument('--seeds',type=int)
    p.add_argument('--seed-start',type=int,default=3000)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    run(args.output,args.suite,args.seed_start,args.seeds or (2 if args.suite=='smoke' else 30))
