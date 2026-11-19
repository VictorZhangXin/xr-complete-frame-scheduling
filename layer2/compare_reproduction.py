import csv,json,math,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
old=ROOT/'results/research_loop';new=ROOT/'results/research_loop_v3_2'
report={'same_seeds_not_new_evidence':True,'phases':{}}
for phase in ('calibration','validation'):
    left=list(csv.DictReader((old/phase/'runs.csv').open(encoding='utf-8')))
    right=list(csv.DictReader((new/phase/'runs.csv').open(encoding='utf-8')))
    if len(left)!=len(right):raise ValueError('Length')
    for x,y in zip(left,right):
        if x.keys()!=y.keys():raise ValueError('Schema')
        for k,v in x.items():
            if v==y[k]:continue
            try:equal=math.isclose(float(v),float(y[k]),rel_tol=1e-12,abs_tol=1e-12)
            except ValueError:equal=False
            if not equal:raise ValueError((phase,k,v,y[k]))
    def content_hash(path):
        h=hashlib.sha256()
        with gzip.open(path,'rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        return h.hexdigest()
    lh=content_hash(old/phase/'frames.csv.gz');rh=content_hash(new/phase/'frames.csv.gz')
    if lh!=rh:raise ValueError('Frame content differs')
    report['phases'][phase]={'runs':len(left),'all_columns_equal_with_tolerance':True,'frame_content_sha256':rh,'frame_content_identical':True}
if json.loads((old/'frozen_selection.json').read_text())!=json.loads((new/'frozen_selection.json').read_text()):raise ValueError('Selection changed')
report['frozen_selection_identical']=True
(ROOT/'review/reproduction_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
