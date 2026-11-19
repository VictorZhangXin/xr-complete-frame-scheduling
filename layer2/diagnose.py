"""Reconstruct new source/overflow diagnostics independently from frame records."""
import csv,gzip,itertools,math,json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results/stress_3000'
def key(r):return (r['scenario'],r['seed'],r['policy'],float(r['alpha']))
def main():
    runs=list(csv.DictReader((RESULTS/'runs.csv').open(encoding='utf-8')))
    lookup={key(r):r for r in runs}
    sources={(*key(r),int(r['source'])):r for r in csv.DictReader((RESULTS/'sources.csv').open(encoding='utf-8'))}
    seen=set()
    with gzip.open(RESULTS/'frames.csv.gz','rt',encoding='utf-8') as f:
        for identity,group in itertools.groupby(csv.DictReader(f),key):
            frames=list(group);r=lookup[identity];seen.add(identity);rates=[]
            for source in range(int(r['cfg_sources'])):
                group=[x for x in frames if int(x['source'])==source]
                complete=sum(x['status']=='complete' for x in group)
                rate=complete/len(group);rates.append(rate)
                row=sources[(*identity,source)]
                if int(row['generated'])!=len(group) or int(row['completed'])!=complete or not math.isclose(float(row['complete_fraction']),rate):raise ValueError('Source mismatch')
            checks={'source_min_completion':min(rates),'source_completion_gap':max(rates)-min(rates),'overflow_high_frames':sum(x['status']=='overflow' and x['high']=='True' for x in frames),'ordinary_floor_breached':int(float(r['low_completion_fraction'])<.70)}
            if not all(math.isclose(float(r[k]),v) for k,v in checks.items()):raise ValueError('Diagnostic mismatch')
    if len(seen)!=len(runs):raise ValueError('Missing group')
    effects=list(csv.DictReader((RESULTS/'paired_effects.csv').open()))
    edf=list(csv.DictReader((RESULTS/'edf_safe_comparison/paired_effects.csv').open()))
    def estimate(rows,scenario,metric):
        r=next(r for r in rows if int(r['scenario'])==scenario and r['metric']==metric)
        return f"{100*float(r['mean_delta']):+.3f} [{100*float(r['ci_low']):+.3f}, {100*float(r['ci_high']):+.3f}]"
    lines=['# V3 压力实验实际结果','', '450次运行、323970条帧记录、1800条每源记录已核验。区间为逐项配对95% t区间，单位百分点；压力比较为探索性，未进行跨场景多重校正。', '', '| 设置 | 加权 FA1−FA0 | 普通 FA1−FA0 | 加权 FA1−EDF-safe |','|---|---|---|---|']
    for i,name in enumerate(['IID对照','40包缓冲区','Markov突发失败']):
        lines.append(f'|{name}|{estimate(effects,i,"weighted_fraction")}|{estimate(effects,i,"low_completion_fraction")}|{estimate(edf,i,"weighted_fraction")}|')
    lines+=['','| 设置 | FA1每运行平均溢出帧 | 其中重要帧 | FA1最低源完整率均值 | 源间极差均值 | 普通完整率低于70%的运行 |','|---|---|---|---|---|---|']
    for i,name in enumerate(['IID对照','40包缓冲区','Markov突发失败']):
        rr=[r for r in runs if int(r['scenario'])==i and r['policy']=='FA' and float(r['alpha'])==1]
        avg=lambda k:sum(float(r[k]) for r in rr)/len(rr)
        lines.append(f'|{name}|{avg("overflow_frames"):.2f}|{avg("overflow_high_frames"):.2f}|{avg("source_min_completion"):.3f}|{avg("source_completion_gap"):.3f}|{int(sum(float(r["ordinary_floor_breached"]) for r in rr))}/30|')
    lines+=['','容量压力下FA1相对FA0的加权区间跨零，且低于EDF-safe；不能把原拥塞场景的优势推广到有限缓冲区。突发失败下仍观察到权重取舍，但只检验了一个rho参数，不代表真实信道验证。70%只是预先记录的示例底线；每源平均指标也不等于长期公平性保证。','', '本轮未引入普通帧保障算法，没有根据压力结果调参；后续可先讨论是否接受普通帧损失，再决定是否需要另开保障机制实验。']
    (ROOT/'review/STRESS_RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'runs':len(seen),'source_rows':len(sources),'diagnostics_audit':'passed'}))
if __name__=='__main__':main()
