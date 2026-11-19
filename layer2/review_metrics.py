"""Supplementary comparisons; no simulation or parameter selection changes."""
import json
import analyze_study as a

def supplement(dest,rows,admission,label,ci):
    a.save_csv(dest/'admission_breakdown.csv',admission)
    lines=['','## 选定策略与强基线 EDF-safe','', '以下全部为选定策略减EDF-safe，单位百分点；逐项95%配对区间，不只报告有利场景。','', '| 容量 | 背景 | 加权完整率变化 | 总完整率变化 | 普通完整率变化 |','|---|---|---|---|---|']
    for scene in range(13):
        r=next(r for r in rows if int(r['scenario'])==scene)
        lines.append(f'|{r["capacity"]} {r["family"]}|{r["background"]}|{ci(scene,label,"EDF_safe","weighted_fraction")}|{ci(scene,label,"EDF_safe","complete_fraction")}|{ci(scene,label,"EDF_safe","low_completion_fraction")}|')
    lines+=['','## 分开核算准入失败','', '| 策略 背景45%容量40 | 生成帧 | 超大帧拒绝 | 占用拒绝 | 超大帧占所有帧 | 超大帧占溢出 |','|---|---|---|---|---|---|']
    for policy in ('FA0',label,'FA1','EDF_safe'):
        rr=[r for r in admission if int(r['scenario'])==1 and r['policy']==policy]
        total=sum(r['generated'] for r in rr)
        big=sum(r['high_oversized_rejected']+r['ordinary_oversized_rejected'] for r in rr)
        occupied=sum(r['high_occupied_rejected']+r['ordinary_occupied_rejected'] for r in rr)
        lines.append(f'|{policy}|{total}|{big}|{occupied}|{big/total:.2%}|{big/(big+occupied):.2%}|')
    lines+=['','超大帧指初始包数严格大于队列总容量，即使空队列也无法准入；占用拒绝指帧本身放得下，但入队时剩余空间不足。数字为30种子之和，每策略单独统计，同一帧在不同策略间重复出现不能当成新增独立样本。队列容量改变也改变准入帧大小构成，因此不将全部拒绝归因为动态拥塞。']
    metric_names=('weighted_fraction','complete_fraction','high_completion_fraction','low_completion_fraction','wasted_bytes','waste_share')
    signatures={}
    for scene in range(13):
        records=sorted([r for r in rows if int(r['scenario'])==scene],key=lambda r:(int(r['seed']),r['policy']))
        signature=tuple((int(r['seed']),r['policy'],*(float(r[m]) for m in metric_names)) for r in records)
        signatures.setdefault(signature,[]).append(scene)
    groups=list(signatures.values())
    completion_groups={}
    for scene in range(13):
        records=sorted([r for r in rows if int(r['scenario'])==scene],key=lambda r:(int(r['seed']),r['policy']))
        signature=tuple((int(r['seed']),r['policy'],*(float(r[m]) for m in metric_names[:4])) for r in records)
        completion_groups.setdefault(signature,[]).append(scene)
    (dest/'equivalent_scenarios.json').write_text(json.dumps({'metrics':metric_names,'groups':groups,'distinct_result_groups':len(groups),'completion_only_groups':list(completion_groups.values()),'completion_only_count':len(completion_groups),'claim':'Equivalence is metric-specific; not independent environments or theoretical equivalence.'},indent=2),encoding='utf-8')
    lines+=['','## 重复条件与证据强度','',f'按每种策略每个种子的六项核心指标精确比较，13个配置形成{len(groups)}组不同数值结果；完全相同结果组为{[g for g in groups if len(g)>1]}。如果只比较四类完成率，则为{len(completion_groups)}组，160与4096包在三个背景条件下均重合。少数运行的浪费字节不同，因此复审报告“实际只有10组不同结果”的说法必须限定到完成率，不能推广到全部指标。', '相同完成率支持当前轨迹下完成表现不再受该容量变化影响，并不证明队列行为完全相同。不同配置也复用种子，因此10组或12组数值结果都不是独立环境样本数。']
    return lines
