"""Reproduce selected V2 defects without editing its files."""
import importlib.util,tempfile,json,ast
from pathlib import Path
import study
ROOT=Path(__file__).resolve().parent
path=ROOT/'baseline/xr_importance/v2/analyze_study.py'
spec=importlib.util.spec_from_file_location('original_analysis',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
rows=[]
for seed in range(3):
    for alpha in (0,1):
        rows.append({'scenario':0,'seed':seed,'policy':'FA','alpha':alpha,'family':'main',**{k:float('nan') if seed==2 and alpha==1 else .5+.1*alpha for k in module.METRICS}})
with tempfile.TemporaryDirectory() as tmp:
    module.OUT=Path(tmp)
    summary,effects=module.summarize(rows)
    observed=next(r for r in summary if r['alpha']==1 and r['metric']=='weighted_fraction')
    result={'original_summary_reported_n':observed['n'],'actual_finite_n':2,'original_bootstrap_nan':str(effects[0]['bootstrap_low']),
            'original_assert_count':sum(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(path.read_text(encoding='utf-8')))),
            'v2_verifier_source':(ROOT/'baseline/xr_importance/verify_v2.py').read_text()}
(ROOT/'review/defect_probes.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
