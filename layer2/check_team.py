import sys,json,csv,math,subprocess
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parent
repo=ROOT/'team_reference/repository';sys.path.insert(0,str(repo))
from sim34.model import Params,Frame,p_complete,simulate
from sim34.policies import POLICIES
proc=subprocess.run([sys.executable,'-m','sim34.validate'],cwd=repo,capture_output=True,text=True)
(ROOT/'team_reference/validation.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
if proc.returncode:raise ValueError('Team tests failed')
raw=list(csv.DictReader((repo/'results/raw_main.csv').open()))
matches=0
for row in raw:
    if float(row['load'])==.6 and float(row['loss'])==.01:
        r=simulate(Params(seed=int(row['seed']),bg_load=.6,p_loss=.01),POLICIES[row['policy']])
        for key in ('cfr','iw_cfr','waste','cfr_a','cfr_b'):
            if not math.isclose(r[key],float(row[key]),abs_tol=1e-12):raise ValueError(key)
        matches+=1
# Equal weights still produce different ordering; no ambiguous probability threshold.
p=Params(bg_load=0,p_loss=0)
fs=[Frame(0,'A',0,3,2,1,2),Frame(1,'B',0,4,1,1,1)]
edf=POLICIES['CA-EDF'](fs,0,p).fid;vd=POLICIES['CA-VD'](fs,0,p).fid
# One slot, two opportunities jointly blocked: exact P(two successes)=0.5.
f=Frame(0,'A',0,1,2,1,2)
estimated=p_complete(f,0,Params(bg_load=.5,p_loss=0,pkts_per_slot=2))
out={'replayed_runs':matches,'equal_weight_CA_EDF_choice':edf,'equal_weight_CA_VD_choice':vd,'one_slot_exact_probability':.5,'normal_binomial_estimate':estimated,'note':'Shared slot blockage correlates opportunities; estimated completion is not exact nor competition-aware.'}
(ROOT/'team_reference/independent_checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
