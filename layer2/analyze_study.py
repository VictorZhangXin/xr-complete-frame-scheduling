from integrity import safe_relative
import csv
import gzip
import hashlib
import itertools
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT
sys.path.insert(0, str(PROJECT / '.deps'))
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT / '.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

OUT = ROOT / 'results'
METRICS = ('weighted_fraction', 'complete_fraction', 'high_completion_fraction',
           'low_completion_fraction', 'wasted_bytes', 'waste_share')


def load_rows():
    with (OUT / 'runs.csv').open(encoding='utf-8') as source:
        return [{key: value if key in ('family', 'policy', 'trace_sha256') else float(value)
                 for key, value in row.items()} for row in csv.DictReader(source)]


def key(row):
    return int(row['scenario']), int(row['seed']), row['policy'], float(row['alpha'])


def select(rows, **criteria):
    return [row for row in rows if all(row[name] == value for name, value in criteria.items())]


def interval(values):
    array = np.asarray(values, float)
    array = array[np.isfinite(array)]
    if len(array) < 2:
        return float(array.mean()) if len(array) else math.nan, math.nan, math.nan
    mean = float(array.mean())
    half = float(student_t.ppf(0.975, len(array) - 1) * array.std(ddof=1) / math.sqrt(len(array)))
    return mean, mean - half, mean + half


def save_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(rows):
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    expected_runs = sum(len(item['policies']) for item in manifest['scenarios']) * len(manifest['seeds'])
    if not (len(rows) == expected_runs):
        raise AssertionError('Integrity check failed: len(rows) == expected_runs')
    lookup = {key(row): row for row in rows}
    if not (len(lookup) == len(rows)):
        raise AssertionError('Integrity check failed: len(lookup) == len(rows)')
    for filename, expected_hash in manifest['sha256'].items():
        if not (hashlib.sha256(safe_relative(PROJECT, filename).read_bytes()).hexdigest() == expected_hash):
            raise AssertionError('Integrity check failed: hashlib.sha256(safe_relative(PROJECT, filename).read_bytes()).hexdigest() == expected_hash')
    for scenario_id, item in enumerate(manifest['scenarios']):
        for seed in manifest['seeds']:
            paired = []
            for policy, alpha in item['policies']:
                row = lookup[(scenario_id, seed, policy, alpha)]
                for name, value in item['config'].items():
                    if not (row['cfg_' + name] == value):
                        raise AssertionError("Integrity check failed: row['cfg_' + name] == value")
                paired.append(row)
            if not (len({row['trace_sha256'] for row in paired}) == 1):
                raise AssertionError("Integrity check failed: len({row['trace_sha256'] for row in paired}) == 1")
            if item['family'] == 'main':
                fifo = lookup[(scenario_id, seed, 'FIFO', 0)]
                edf = lookup[(scenario_id, seed, 'EDF', 0)]
                if not (all(fifo[name] == edf[name] for name in METRICS)):
                    raise AssertionError('Integrity check failed: all(fifo[name] == edf[name] for name in METRICS)')
    seen_runs = set()
    frame_count = 0
    run_count = 0
    with gzip.open(OUT / 'frames.csv.gz', 'rt', newline='', encoding='utf-8') as source:
        for identity, group in itertools.groupby(csv.DictReader(source), key=key):
            if identity in seen_runs:
                raise ValueError("Repeated frame group")
            seen_runs.add(identity)
            run = lookup[identity]
            completed = high = completed_high = packets = delivered = attempts = wasted = received_waste = retries = 0
            value_total = value_done = 0.0
            identifiers = set()
            for frame in group:
                identifier = int(frame['identifier'])
                if not (identifier not in identifiers):
                    raise AssertionError('Integrity check failed: identifier not in identifiers')
                identifiers.add(identifier)
                packet_count = int(frame['packets'])
                sent = int(frame['attempts'])
                received = int(frame['delivered'])
                remaining = int(frame['remaining'])
                is_high = frame['high'] == 'True'
                success = frame['status'] == 'complete'
                if not (packet_count == received + remaining and sent >= received):
                    raise AssertionError('Integrity check failed: packet_count == received + remaining and sent >= received')
                if not (float(frame['value']) == (run['cfg_high_value'] if is_high else 1.0)):
                    raise AssertionError("Integrity check failed: float(frame['value']) == (run['cfg_high_value'] if is_high else 1.0)")
                if success:
                    if not (remaining == 0 and int(frame['completion']) <= int(frame['deadline'])):
                        raise AssertionError("Integrity check failed: remaining == 0 and int(frame['completion']) <= int(frame['deadline'])")
                    retries += sent - packet_count
                else:
                    if not (not frame['completion']):
                        raise AssertionError("Integrity check failed: not frame['completion']")
                    wasted += sent
                    received_waste += received
                high += is_high
                completed += success
                completed_high += is_high and success
                packets += packet_count
                delivered += received
                attempts += sent
                value_total += float(frame['value'])
                value_done += float(frame['value']) * success
            total = len(identifiers)
            if not (identifiers == set(range(total))):
                raise AssertionError('Integrity check failed: identifiers == set(range(total))')
            checks = {'generated_frames': total, 'high_frames': high, 'completed_frames': completed,
                      'completed_high_frames': completed_high, 'generated_packets': packets,
                      'delivered_packets': delivered, 'attempts': attempts,
                      'total_frame_value': value_total, 'completed_frame_value': value_done,
                      'complete_fraction': completed / total if total else math.nan, 'weighted_fraction': value_done / value_total if value_total else math.nan,
                      'high_completion_fraction': completed_high / high if high else math.nan,
                      'low_completion_fraction': (completed - completed_high) / (total - high) if total != high else math.nan,
                      'wasted_bytes': wasted * run['cfg_packet_bytes'],
                      'wasted_received_bytes': received_waste * run['cfg_packet_bytes'],
                      'completed_retry_bytes': retries * run['cfg_packet_bytes']}
            if not (all((math.isnan(run[name]) and math.isnan(value)) or math.isclose(run[name], value, abs_tol=1e-10) for name, value in checks.items())):
                raise AssertionError('Integrity check failed: all((math.isnan(run[name]) and math.isnan(value)) or math.isclose(run[name], value, abs_tol=1e-10) for name, value in checks.items())')
            if not (run['attempted_bytes'] == run['wasted_bytes'] + run['useful_payload_bytes'] + run['completed_retry_bytes']):
                raise AssertionError("Integrity check failed: run['attempted_bytes'] == run['wasted_bytes'] + run['useful_payload_bytes'] + run['completed_retry_bytes']")
            if not (run['attempts'] + run['idle_slots'] + run['background_slots'] == run['horizon_slots']):
                raise AssertionError("Integrity check failed: run['attempts'] + run['idle_slots'] + run['background_slots'] == run['horizon_slots']")
            frame_count += total
            run_count += 1
    if not (seen_runs == set(lookup)):
        raise AssertionError('Integrity check failed: seen_runs == set(lookup)')
    if not (run_count == expected_runs):
        raise AssertionError('Integrity check failed: run_count == expected_runs')
    result = {'runs': run_count, 'frame_rows_independently_reaggregated': frame_count,
              'scenario_seed_traces': len(manifest['scenarios']) * len(manifest['seeds']),
              'source_hashes_verified': True, 'all_config_fields_preserved': True,
              'paired_traces_equal': True, 'frame_metrics_reconstructed': True,
              'resource_conservation': True, 'FIFO_equals_EDF': True,
              'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return result


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row['scenario'], row['policy'], row['alpha'])].append(row)
    summary = []
    for (scenario, policy, alpha), group in grouped.items():
        for metric in METRICS:
            values = [row[metric] for row in group]
            mean, lower, upper = interval(values)
            summary.append({'scenario': int(scenario), 'policy': policy, 'alpha': alpha, 'metric': metric,
                            'n': sum(math.isfinite(v) for v in values), 'n_total': len(values), 'mean': mean, 'ci_low': lower, 'ci_high': upper})
    effects = []
    for scenario in sorted({row['scenario'] for row in rows}):
        first = {row['seed']: row for row in select(rows, scenario=scenario, policy='FA', alpha=0)}
        second = {row['seed']: row for row in select(rows, scenario=scenario, policy='FA', alpha=1)}
        if not (first.keys() == second.keys()):
            raise AssertionError('Integrity check failed: first.keys() == second.keys()')
        for metric_index, metric in enumerate(METRICS):
            differences = np.array([second[seed][metric] - first[seed][metric] for seed in sorted(first)])
            n_total = len(differences)
            differences = differences[np.isfinite(differences)]
            mean, lower, upper = interval(differences)
            rng = np.random.default_rng(90000 + int(scenario) * 100 + metric_index)
            if len(differences) >= 2:
                bootstrap_means = differences[rng.integers(0, len(differences), (10000, len(differences)))].mean(axis=1)
                bootstrap_lower, bootstrap_upper = np.quantile(bootstrap_means, [0.025, 0.975])
                deviation = differences.std(ddof=1)
                probability = float(2 * student_t.sf(abs(mean) / (deviation / math.sqrt(len(differences))), len(differences) - 1)) if deviation else float(mean == 0)
            else:
                bootstrap_lower = bootstrap_upper = probability = math.nan
            sample = next(iter(first.values()))
            effects.append({'scenario': int(scenario), 'family': sample['family'], 'metric': metric,
                            'n': len(differences), 'n_total': n_total, 'mean_delta': mean, 'ci_low': lower, 'ci_high': upper,
                            'bootstrap_low': float(bootstrap_lower), 'bootstrap_high': float(bootstrap_upper),
                            'p_two_sided': probability, 'p_holm_main_weighted': ''})
    main_tests = sorted([effect for effect in effects if effect['family'] == 'main' and effect['metric'] == 'weighted_fraction' and math.isfinite(effect['p_two_sided'])], key=lambda effect: effect['p_two_sided'])
    previous = 0
    for index, effect in enumerate(main_tests):
        adjusted = min(1, max(previous, effect['p_two_sided'] * (len(main_tests) - index)))
        effect['p_holm_main_weighted'] = adjusted
        previous = adjusted
    save_csv(OUT / 'summary.csv', summary)
    save_csv(OUT / 'paired_effects.csv', effects)
    return summary, effects


def figures(rows, effects):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.alpha': 0.20})
    backgrounds = (0, 0.15, 0.30, 0.45, 0.60)
    def save(figure, name):
        figure.savefig(OUT / (name + '.png'), dpi=200, facecolor='white')
        figure.savefig(OUT / (name + '.svg'), facecolor='white')
        plt.close(figure)
    figure, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), layout='constrained')
    for axis, metric, title, scale in zip(axes.flat,
            ('weighted_fraction', 'complete_fraction', 'low_completion_fraction', 'wasted_bytes'),
            ('Weighted completion (%)', 'All-frame completion (%)', 'Ordinary-frame completion (%)', 'Incomplete-frame transmission (MB)'),
            (100, 100, 100, 1e-6)):
        for policy, alpha, display, color in [('FIFO', 0, 'FIFO = EDF', '#9a6a35'), ('EDF-safe', 0, 'EDF-safe', '#68788c'),
                                             ('FA', 0, 'FA(0)', '#2375af'), ('FA', 1, 'FA(1)', '#be4639')]:
            estimates = np.array([interval([row[metric] * scale for row in select(rows, family='main', cfg_background=background,
                         cfg_size_cv=0.5, cfg_loss=0.1, policy=policy, alpha=alpha)]) for background in backgrounds])
            axis.errorbar(np.array(backgrounds) * 100, estimates[:, 0], yerr=estimates[:, 2] - estimates[:, 0],
                          color=color, marker='o', capsize=3, label=display)
        axis.set(title=title, xlabel='Background occupancy (%)', ylim=(0, 103) if scale == 100 else (0, None))
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc='outside lower center', ncol=4, frameon=False)
    figure.suptitle('CV 0.50 | attempt failure 10% | 30 independent paired seeds', fontsize=12)
    save(figure, 'figure1_main')
    figure, axes = plt.subplots(1, 3, figsize=(12.5, 4.4), layout='constrained')
    for axis, metric, title, scale in zip(axes, ('weighted_fraction', 'low_completion_fraction', 'wasted_bytes'),
                                         ('Weighted change (pp)', 'Ordinary-frame change (pp)', 'Wasted-byte change (MB)'), (100, 100, 1e-6)):
        for cv, loss, color in ((0.1, 0, '#297b66'), (0.1, 0.1, '#d19135'), (0.5, 0, '#2375af'), (0.5, 0.1, '#be4639')):
            scenario_ids = [select(rows, family='main', cfg_background=background, cfg_size_cv=cv, cfg_loss=loss)[0]['scenario'] for background in backgrounds]
            estimates = [select(effects, scenario=scenario, metric=metric)[0] for scenario in scenario_ids]
            axis.errorbar(np.array(backgrounds) * 100, [effect['mean_delta'] * scale for effect in estimates],
                          yerr=[(effect['ci_high'] - effect['mean_delta']) * scale for effect in estimates],
                          label=f'CV {cv}, loss {loss:.0%}', marker='o', capsize=3, color=color)
        axis.axhline(0, color='black', linewidth=0.8)
        axis.set(title=title, xlabel='Background occupancy (%)')
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc='outside lower center', ncol=4, frameon=False)
    figure.suptitle('FA(1) minus FA(0) | paired 95% t intervals', fontsize=12)
    save(figure, 'figure2_paired')
    figure, axes = plt.subplots(1, 3, figsize=(12.5, 4.4), layout='constrained')
    for axis, field, settings, family, title in zip(axes, ('alpha', 'cfg_high_value', 'cfg_high_fraction'),
            ((0, 0.25, 0.5, 1, 2), (2, 4, 8), (0.1, 0.25, 0.5)),
            ('main', 'value_sensitivity', 'share_sensitivity'),
            ('Scheduling exponent', 'High-frame value', 'High-frame share')):
        if field == 'alpha':
            for metric, display, color in [('weighted_fraction', 'Weighted completion', '#2375af'), ('low_completion_fraction', 'Ordinary completion', '#be4639')]:
                estimates = np.array([interval([row[metric] * 100 for row in select(rows, family='main', policy='FA', alpha=setting,
                                  cfg_background=0.45, cfg_size_cv=0.5, cfg_loss=0.1)]) for setting in settings])
                axis.errorbar(settings, estimates[:, 0], yerr=estimates[:, 2] - estimates[:, 0], marker='o', capsize=3, label=display, color=color)
            axis.set_ylabel('Completion (%)')
        else:
            for metric, display, color in [('weighted_fraction', 'Weighted change', '#2375af'), ('low_completion_fraction', 'Ordinary change', '#be4639')]:
                estimates = []
                for setting in settings:
                    selected_family = 'main' if setting in (4, 0.25) else family
                    scenario = select(rows, family=selected_family, cfg_background=0.45, cfg_size_cv=0.5, cfg_loss=0.1, **{field: setting})[0]['scenario']
                    estimates.append(select(effects, scenario=scenario, metric=metric)[0])
                axis.errorbar(settings, [effect['mean_delta'] * 100 for effect in estimates],
                              yerr=[(effect['ci_high'] - effect['mean_delta']) * 100 for effect in estimates],
                              marker='o', capsize=3, label=display, color=color)
            axis.axhline(0, color='black', linewidth=0.8)
            axis.set_ylabel('Paired change (pp)')
        axis.set_xlabel(title)
        axis.legend(fontsize=8, frameon=False)
    figure.suptitle('Sensitivity at 45% background | CV 0.50 | attempt failure 10%', fontsize=12)
    save(figure, 'figure3_sensitivity')

