"""Read-only input validation. Reports go only to an explicit new report directory."""
import argparse, csv, json, math, tempfile, hashlib
from pathlib import Path, PurePosixPath
import analyze_study as a
import study as s
from integrity import hashes, write_json

ROOT=Path(__file__).resolve().parent
def verify(report):
    report=Path(report)
    if report.exists():raise FileExistsError(report)
    baseline=ROOT/'baseline/xr_importance'
    before=hashes(baseline)
    a.PROJECT=baseline;a.OUT=baseline/'v2/results'
    rows=a.load_rows();audit=a.audit(rows)
    validation=s.validate()
    with tempfile.TemporaryDirectory() as tmp:
        a.OUT=Path(tmp);means,effects=a.summarize(rows)
        for filename,computed in [('summary.csv',means),('paired_effects.csv',effects)]:
            original=list(csv.DictReader((baseline/'v2/results'/filename).open(encoding='utf-8')))
            if len(original)!=len(computed):raise ValueError('Statistics length mismatch')
            for left,right in zip(original,computed):
                for key,value in left.items():
                    if key in ('policy','metric','family') or value=='':
                        if value!=str(right[key]):raise ValueError((key,value,right[key]))
                    elif not math.isclose(float(value),float(right[key]),rel_tol=1e-12,abs_tol=1e-12):raise ValueError((key,value,right[key]))
    # Independent full V2 rerun (all saved runs), compares input hashes and all shared metrics.
    manifest=json.loads((baseline/'v2/results/manifest.json').read_text())
    lookup={(int(r['scenario']),int(r['seed']),r['policy'],r['alpha']):r for r in rows}
    replayed=0
    for scenario,item in enumerate(manifest['scenarios']):
        config=s.Config(**item['config'])
        for seed in manifest['seeds']:
            trace=s.make_trace(config,seed)
            for policy,alpha in item['policies']:
                saved=lookup[(scenario,seed,policy,alpha)]
                if trace.fingerprint()!=saved['trace_sha256']:raise ValueError('Replay trace mismatch')
                metrics,_=s.checked_simulate(trace,config,policy,alpha)
                for k,v in metrics.items():
                    if not math.isclose(saved[k],v,rel_tol=1e-12,abs_tol=1e-12):raise ValueError(('Replay metric',k))
                replayed+=1
        print('Replayed scenario '+str(scenario),flush=True)
    if hashes(baseline)!=before:raise ValueError('Read-only verification modified baseline')
    main=[e for e in effects if e['family']=='main' and e['metric']=='weighted_fraction']
    better=equal=0
    for scenario in range(20):
        get=lambda policy,alpha:next(r['mean'] for r in means if r['scenario']==scenario and r['policy']==policy and r['alpha']==alpha and r['metric']=='weighted_fraction')
        x,y=get('FA',1),get('EDF-safe',0)
        better+=x>y;equal+=x==y
    report.mkdir(parents=True)
    write_json(report/'verification.json',{'audit':audit,'validation':validation,'full_replayed_runs':replayed,'summary_rows':len(means),'effect_rows':len(effects),'baseline_unchanged':True,'overflow_total':sum(r['overflow_frames'] for r in rows),'main_weighted_holm_below_005':sum(e['p_holm_main_weighted']<.05 for e in main),'fa1_above_edf_safe_scenarios':better,'fa1_equal_edf_safe_scenarios':equal,'linux_path_issue_semantic_probe':str(PurePosixPath('v2\\study.py').parts),'native_linux_test':False})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);args=p.parse_args();verify(args.report)
