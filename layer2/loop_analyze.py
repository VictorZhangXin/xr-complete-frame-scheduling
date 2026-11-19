import csv,gzip,json,itertools,math,hashlib
from pathlib import Path
from collections import Counter
import analyze_study as a

def key(r):return int(r['scenario']),int(r['seed']),r['policy']
def _analyze(root, dest, source_root):
    root=Path(root);rows=[];frame_count=0;admission=[]
    manifest=json.loads((root/'manifest.json').read_text())
    from integrity import safe_relative
    for name,expected in manifest['sha256'].items():
        if hashlib.sha256(safe_relative(source_root,name).read_bytes()).hexdigest()!=expected:raise ValueError('Source hash mismatch')
    for phase in ('calibration','validation'):
        rr=list(csv.DictReader((root/phase/'runs.csv').open(encoding='utf-8')))
        lookup={key(r):r for r in rr};seen=set()
        expected_count=300 if phase=='calibration' else 3120
        if len(lookup)!=len(rr) or len(rr)!=expected_count:raise ValueError('Run count')
        with gzip.open(root/phase/'frames.csv.gz','rt',encoding='utf-8') as ff:
            for identity,group in itertools.groupby(csv.DictReader(ff),key):
                if identity in seen:raise ValueError('Duplicate run')
                seen.add(identity);frames=list(group);r=lookup[identity];frame_count+=len(frames)
                if len({f['identifier'] for f in frames})!=len(frames):raise ValueError('Duplicate frame')
                n=len(frames);done=[f for f in frames if f['status']=='complete'];totalvalue=sum(float(f['value']) for f in frames)
                if phase=='validation':
                    detail={k:r[k] for k in ('scenario','seed','policy','capacity','background','family')}
                    detail['generated']=n
                    detail['oversized_generated']=sum(int(f['packets'])>int(r['capacity']) for f in frames)
                    for group_name,flag in [('high','True'),('ordinary','False')]:
                        dropped=[f for f in frames if f['status']=='overflow' and f['high']==flag]
                        big=[f for f in dropped if int(f['packets'])>int(r['capacity'])]
                        occupied=[f for f in dropped if int(f['packets'])<=int(r['capacity'])]
                        detail[group_name+'_oversized_rejected']=len(big)
                        detail[group_name+'_occupied_rejected']=len(occupied)
                    if sum(detail[k] for k in ('high_oversized_rejected','ordinary_oversized_rejected'))!=detail['oversized_generated']:raise ValueError('Oversize admission invariant')
                    if sum(detail[k] for k in ('high_oversized_rejected','ordinary_oversized_rejected','high_occupied_rejected','ordinary_occupied_rejected'))!=int(r['overflow_frames']):raise ValueError('Overflow partition')
                    admission.append(detail)
                checks={'generated_frames':n,'complete_fraction':len(done)/n,'weighted_fraction':sum(float(f['value']) for f in done)/totalvalue,'attempts':sum(int(f['attempts']) for f in frames),'wasted_bytes':1200*sum(int(f['attempts']) for f in frames if f['status']!='complete')}
                for high,name in [('True','high'),('False','ordinary')]:
                    subset=[f for f in frames if f['high']==high]
                    checks['high_completion_fraction' if high=='True' else 'low_completion_fraction']=sum(f['status']=='complete' for f in subset)/len(subset)
                    for status in ('complete','expired','infeasible','overflow'):
                        g=[f for f in subset if f['status']==status]
                        checks[f'{name}_{status}']=len(g);checks[f'{name}_{status}_attempt_bytes']=1200*sum(int(f['attempts']) for f in g)
                for k,v in checks.items():
                    if not math.isclose(float(r[k]),v,abs_tol=1e-10):raise ValueError(k)
                for f in frames:
                    if int(f['remaining'])+int(f['delivered'])!=int(f['packets']):raise ValueError('Packet conservation')
                    if f['status']=='complete' and (int(f['remaining'])!=0 or int(f['completion'])>int(f['deadline'])):raise ValueError('Completion')
                if float(r['attempted_bytes'])!=float(r['wasted_bytes'])+float(r['useful_payload_bytes'])+float(r['completed_retry_bytes']):raise ValueError('Byte conservation')
            if seen!=set(lookup):raise ValueError('Run coverage')
        for _,g in itertools.groupby(sorted(rr,key=lambda r:(r['scenario'],r['seed'])),lambda r:(r['scenario'],r['seed'])):
            if len({r['trace_sha256'] for r in g})!=1:raise ValueError('Unpaired input')
        if phase=='validation':rows=rr
    chosen=json.loads((root/'frozen_selection.json').read_text())['alpha'];label=f'FA{chosen:g}'
    def pair(scene,left,right,metric):
        x={int(r['seed']):float(r[metric]) for r in rows if int(r['scenario'])==scene and r['policy']==left}
        y={int(r['seed']):float(r[metric]) for r in rows if int(r['scenario'])==scene and r['policy']==right}
        return [x[k]-y[k] for k in sorted(x)]
    def ci(scene,left,right,metric):
        m,lo,hi=a.interval(pair(scene,left,right,metric));return f'{m*100:+.2f} [{lo*100:+.2f}, {hi*100:+.2f}]'
    effects=[]
    for scene in range(13):
        for left,right in [(label,'FA0'),(label,'FA1'),(label,'EDF_safe'),('FA1','FA0'),('FA0','FA0_no_drop'),('FA1','FA1_no_drop'),('FA1','EDF_safe')]:
            for metric in ('weighted_fraction','low_completion_fraction','complete_fraction','waste_share'):
                differences=pair(scene,left,right,metric);m,lo,hi=a.interval(differences)
                effects.append(dict(scenario=scene,left=left,right=right,metric=metric,n=len(differences),mean=m,ci_low=lo,ci_high=hi))
    a.save_csv(dest/'effects.csv',effects)
    lines=['# V3.2 研究闭环结果','',f'校准阶段锁定 alpha={chosen:g}，验证阶段未重新选参。普通帧损失预算2个百分点，属于示例平均取舍，不是逐帧、逐运行或在线保证。','', '| 容量 | 背景 | 选定策略加权增益 vs FA0 pp | 普通帧损失 pp | 损失95%上界≤2pp | 超预算运行数 |','|---|---|---|---|---|---|']
    for scene in range(13):
        r=next(r for r in rows if int(r['scenario'])==scene)
        loss=pair(scene,'FA0',label,'low_completion_fraction');m,lo,hi=a.interval(loss)
        lines.append(f'|{r["capacity"]} {r["family"]}|{r["background"]}|{ci(scene,label,"FA0","weighted_fraction")}|{m*100:.2f} [{lo*100:.2f}, {hi*100:.2f}]|{hi<=.02}|{sum(v>.02 for v in loss)}/30|')
    lines+=['','## 机制分解','', '下表每项为每运行平均失败帧数。普通/重要分别核算；主指标始终按全部生成帧计算，不能只选择准入帧作为新分母。','', '| 容量 背景45% | 策略 | 重要溢出 | 重要超时 | 重要不可行 | 普通溢出 | 普通超时 | 普通不可行 |','|---|---|---|---|---|---|---|---|']
    for scene in (1,4,7,10):
        for policy in ('FA0','FA1',label,'EDF_safe'):
            rs=[r for r in rows if int(r['scenario'])==scene and r['policy']==policy]
            vals=[sum(float(r[f'{cl}_{status}']) for r in rs)/len(rs) for cl in ('high','ordinary') for status in ('overflow','expired','infeasible')]
            lines.append('|'+rs[0]['capacity']+'|'+policy+'|'+'|'.join(f'{v:.2f}' for v in vals)+'|')
    lines+=['','## 提前丢弃消融','', '| 容量 背景45% | FA0开启丢弃的加权变化pp | FA1开启丢弃的加权变化pp | FA1−EDF-safe加权变化pp |','|---|---|---|---|']
    for scene in (1,4,7,10):
        q=next(r['capacity'] for r in rows if int(r['scenario'])==scene)
        lines.append(f'|{q}|{ci(scene,"FA0","FA0_no_drop","weighted_fraction")}|{ci(scene,"FA1","FA1_no_drop","weighted_fraction")}|{ci(scene,"FA1","EDF_safe","weighted_fraction")}|')
    lines+=['','## 解释边界','', '容量改变与弃帧消融都是共享轨迹对照。溢出分解支持识别瓶颈，但不能证明每个拒绝帧若准入就一定完成；选择、占用和调度有相互作用。','温和权重是原算法的受控参数改进，不声称新理论算法。判断是否达标需看普通损失区间上界及独立验证表现；某些场景未达预算也必须保留。上述区间是逐项95%，未进行跨场景同时覆盖校正。',f'在背景45%、容量4096的代表场景，选定策略相对FA1的加权变化为{ci(10,label,"FA1","weighted_fraction")}pp，普通完整率变化为{ci(10,label,"FA1","low_completion_fraction")}pp。减少损失是否值得这项代价，应由小组讨论。']
    from review_metrics import supplement
    lines.extend(supplement(dest,rows,admission,label,ci))
    (dest/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    from integrity import write_json
    write_json(dest/'audit.json',{'frame_records':frame_count,'validation_runs':len(rows),'calibration_runs':300,'paired_inputs':True,'per_frame_reaggregation':True,'source_hashes':True,'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'supplement_sha256':hashlib.sha256((Path(__file__).resolve().parent/'review_metrics.py').read_bytes()).hexdigest()})
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for scene in (1,4,7,10):
        q=next(r['capacity'] for r in rows if int(r['scenario'])==scene)
        xx=[];yy=[]
        for alpha in (0,.125,.25,.5,1):
            name=f'FA{alpha:g}';xx.append(100*a.interval(pair(scene,'FA0',name,'low_completion_fraction'))[0]);yy.append(100*a.interval(pair(scene,name,'FA0','weighted_fraction'))[0])
        axes[0].plot(xx,yy,'o-',label=f'{q} packets')
    axes[0].axvline(2,color='black',linestyle='--');axes[0].set(xlabel='Ordinary completion loss (pp)',ylabel='Weighted gain (pp)',title='Held-out tradeoff at 45% background');axes[0].legend()
    for p in ('FA0','FA1',label):
        means=[sum(float(r['overflow_frames']) for r in rows if int(r['scenario'])==sc and r['policy']==p)/30 for sc in (1,4,7,10)]
        axes[1].plot(['40','80','160','4096'],means,'o-',label=p)
    axes[1].set(xlabel='Buffer capacity (packets)',ylabel='Mean overflow frames per run',title='Admission bottleneck');axes[1].legend()
    fig.savefig(dest/'tradeoff.png',dpi=180);plt.close(fig)


def analyze(root, output=None, source_root=None):
    from integrity import hashes
    import tempfile
    root=Path(root).resolve()
    source_root=Path(source_root or Path(__file__).resolve().parent).resolve()
    before=hashes(root)
    if output is None:
        with tempfile.TemporaryDirectory() as tmp:
            _analyze(root,Path(tmp),source_root)
            result=json.loads((Path(tmp)/'audit.json').read_text())
    else:
        dest=Path(output).resolve()
        if dest==root:
            if not root.name.startswith('.loop-pending-'):raise ValueError('Archive overwrite prohibited')
        else:
            if dest.is_relative_to(root):raise ValueError('Reports must be outside archive')
            dest.mkdir(parents=True,exist_ok=False)
        _analyze(root,dest,source_root)
        result=json.loads((dest/'audit.json').read_text())
    if (output is None or Path(output).resolve()!=root) and hashes(root)!=before:
        raise ValueError('Input changed during audit')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--source-root',type=Path)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--output',type=Path)
    mode.add_argument('--read-only',action='store_true')
    args=p.parse_args()
    print(json.dumps(analyze(args.input,args.output,args.source_root)))
