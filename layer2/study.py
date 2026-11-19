import csv
import gzip
import hashlib
import itertools
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT
sys.path.insert(0, str(PROJECT))
from simulate import Config, Frame, Trace, make_trace, np, planned_scenarios, simulate

OUT = ROOT / 'results'
RENAMES = {'high_fraction': 'high_completion_fraction', 'low_fraction': 'low_completion_fraction'}


def check_config(config):
    for name, value in asdict(config).items():
        if not math.isfinite(value):
            raise ValueError(f'Nonfinite configuration: {name}')
    for name in ('duration_s', 'slot_ms', 'fps', 'mean_packets', 'deadline_ms', 'high_value'):
        if getattr(config, name) <= 0:
            raise ValueError(name)
    for name in ('sources', 'queue_packets', 'packet_bytes'):
        if not isinstance(getattr(config, name), int) or getattr(config, name) <= 0:
            raise ValueError(name)
    for name in ('background', 'loss', 'high_fraction'):
        if not 0 <= getattr(config, name) <= 1:
            raise ValueError(name)
    if config.size_cv < 0 or config.jitter_ms < 0 or config.high_size_multiplier <= 0:
        raise ValueError('Invalid size or jitter parameter')
    if not math.isclose(config.deadline_ms / config.slot_ms, round(config.deadline_ms / config.slot_ms)):
        raise ValueError('Deadline must align with slot boundaries')


def checked_simulate(trace, config, policy, alpha=0):
    check_config(config)
    if not math.isfinite(alpha) or alpha < 0:
        raise ValueError('alpha must be finite and nonnegative')
    if len(trace.available) != len(trace.success):
        raise ValueError('Channel arrays differ in length')
    previous_arrival = -1
    identifiers = set()
    for frame in trace.frames:
        if frame.arrival < previous_arrival or not 0 <= frame.arrival < frame.deadline <= len(trace.available):
            raise ValueError('Invalid frame timeline')
        if frame.identifier in identifiers or frame.packets <= 0 or frame.value <= 0:
            raise ValueError('Invalid frame record')
        identifiers.add(frame.identifier)
        previous_arrival = frame.arrival
    original, outcomes = simulate(trace, config, policy, alpha, True)
    metrics = {RENAMES.get(key, key): value for key, value in original.items()}
    metrics['low_frames'] = len(outcomes) - metrics['high_frames']
    metrics['completed_high_frames'] = sum(item['high'] and item['status'] == 'complete' for item in outcomes)
    metrics['completed_low_frames'] = metrics['completed_frames'] - metrics['completed_high_frames']
    metrics['total_frame_value'] = sum(item['value'] for item in outcomes)
    metrics['completed_frame_value'] = sum(item['value'] for item in outcomes if item['status'] == 'complete')
    metrics['realized_high_share'] = metrics['high_frames'] / len(outcomes) if outcomes else math.nan
    metrics['realized_background_fraction'] = metrics['background_slots'] / metrics['horizon_slots'] if metrics['horizon_slots'] else math.nan
    metrics['attempt_failure_fraction'] = 1 - metrics['delivered_packets'] / metrics['attempts'] if metrics['attempts'] else math.nan
    metrics['wasted_mbps'] = metrics['wasted_bytes'] * 8 / config.duration_s / 1e6
    for count, metric in [('high_frames', 'high_completion_fraction'), ('low_frames', 'low_completion_fraction'),
                          ('generated_frames', 'complete_fraction'), ('generated_frames', 'weighted_fraction')]:
        if metrics[count] == 0:
            metrics[metric] = math.nan
    if metrics['attempts'] == 0:
        metrics['waste_share'] = math.nan
    if metrics['generated_packets'] == 0:
        metrics['packet_delivery_fraction'] = math.nan
    return metrics, outcomes


def scenarios():
    yield from planned_scenarios()
    for value in (2.0, 8.0):
        for background in (0.30, 0.45, 0.60):
            yield 'value_sensitivity', Config(background=background, high_value=value), [('FA', 0.0), ('FA', 1.0)]
    for share in (0.10, 0.50):
        for background in (0.30, 0.45, 0.60):
            yield 'share_sensitivity', Config(background=background, high_fraction=share), [('FA', 0.0), ('FA', 1.0)]


def validate():
    checks = []
    config = Config()
    def trace(frames, availability, successes=None):
        return Trace(tuple(frames), np.array(availability, bool), np.array(successes if successes is not None else availability, bool))
    hand = trace([Frame(0, 0, 0, 6, 6, 4, True), Frame(1, 1, 0, 6, 3, 1, False),
                  Frame(2, 2, 0, 6, 3, 1, False)], [1] * 6)
    baseline, _ = checked_simulate(hand, config, 'FA', 0)
    proposed, _ = checked_simulate(hand, config, 'FA', 1)
    if not (baseline['weighted_fraction'] == 1 / 3 and proposed['weighted_fraction'] == 2 / 3):
        raise AssertionError("Integrity check failed: baseline['weighted_fraction'] == 1 / 3 and proposed['weighted_fraction'] == 2 / 3")
    checks.append('Hand-calculated weighted tradeoff')
    for available in itertools.product((False, True), repeat=3):
        for successes in itertools.product((False, True), repeat=3):
            item = trace([Frame(0, 0, 0, 3, 2, 4, True)], available, successes)
            expected = int(sum(first and second for first, second in zip(available, successes)) >= 2)
            for policy in ('FIFO', 'EDF', 'EDF-safe', 'FA'):
                metric, _ = checked_simulate(item, config, policy, 1)
                if not (metric['completed_frames'] == expected):
                    raise AssertionError("Integrity check failed: metric['completed_frames'] == expected")
    checks.append('Exhaustive 64 three-slot channels agree with single-frame oracle for all four policy types')
    late = trace([Frame(0, 0, 2, 4, 2, 4, True)], [1] * 4)
    metric, outcome = checked_simulate(late, config, 'FA')
    if not (outcome[0]['completion'] == 4 and math.isnan(metric['low_completion_fraction'])):
        raise AssertionError("Integrity check failed: outcome[0]['completion'] == 4 and math.isnan(metric['low_completion_fraction'])")
    checks.append('Deadline equality and absent-class NaN')
    metric, _ = checked_simulate(trace([], [1, 1]), config, 'FA')
    if not (math.isnan(metric['weighted_fraction']) and math.isnan(metric['waste_share'])):
        raise AssertionError("Integrity check failed: math.isnan(metric['weighted_fraction']) and math.isnan(metric['waste_share'])")
    checks.append('Empty denominators are missing, not zero failures')
    metric, _ = checked_simulate(hand, replace(config, queue_packets=2), 'FA')
    if not (metric['overflow_frames'] == 3 and metric['generated_frames'] == 3):
        raise AssertionError("Integrity check failed: metric['overflow_frames'] == 3 and metric['generated_frames'] == 3")
    checks.append('Overflow remains in denominator')
    for invalid in (replace(config, loss=1.2), replace(config, slot_ms=0), replace(config, size_cv=-1),
                    replace(config, deadline_ms=0.13), replace(config, high_fraction=-0.1)):
        try:
            check_config(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Bad configuration accepted')
    checks.append('Invalid configurations rejected')
    for seed in (7, 11, 29):
        generated = make_trace(config, seed)
        if not (generated.fingerprint() == make_trace(config, seed).fingerprint()):
            raise AssertionError('Integrity check failed: generated.fingerprint() == make_trace(config, seed).fingerprint()')
        uniform = replace(generated, frames=tuple(replace(frame, value=1) for frame in generated.frames))
        first, _ = checked_simulate(uniform, config, 'FA', 0)
        second, _ = checked_simulate(uniform, config, 'FA', 2)
        if not (first == second):
            raise AssertionError('Integrity check failed: first == second')
        if not (simulate(generated, config, 'FIFO') == simulate(generated, config, 'EDF')):
            raise AssertionError("Integrity check failed: simulate(generated, config, 'FIFO') == simulate(generated, config, 'EDF')")
    checks.extend(['Reproducible trace', 'Equal weights produce identical decisions', 'FIFO equals EDF under common relative deadlines'])
    original_manifest = json.loads((PROJECT / 'baseline' / 'xr_importance' / 'results' / 'manifest.json').read_text(encoding='utf-8'))
    with (PROJECT / 'baseline' / 'xr_importance' / 'results' / 'runs.csv').open(encoding='utf-8') as source:
        legacy_rows = [row for row in csv.DictReader(source) if row['seed'] == '1000']
    for row in legacy_rows:
        legacy_config = Config(**original_manifest['scenarios'][int(row['scenario'])]['config'])
        generated = make_trace(legacy_config, 1000)
        if not (generated.fingerprint() == row['trace_sha256']):
            raise AssertionError("Integrity check failed: generated.fingerprint() == row['trace_sha256']")
        metric, _ = checked_simulate(generated, legacy_config, row['policy'], float(row['alpha']))
        for name in ('weighted_fraction', 'complete_fraction', 'wasted_bytes', 'attempted_bytes'):
            if not (math.isclose(metric[name], float(row[name]), abs_tol=1e-12)):
                raise AssertionError('Integrity check failed: math.isclose(metric[name], float(row[name]), abs_tol=1e-12)')
    checks.append(f'Legacy regression: all {len(legacy_rows)} seed-1000 runs reproduce published metrics and trace hashes')
    result = {'passed_groups': len(checks), 'checks': checks}
    return result

