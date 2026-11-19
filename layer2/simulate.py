from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
import numpy as np


@dataclass(frozen=True)
class Config:
    duration_s: float = 3.0
    slot_ms: float = 0.125
    sources: int = 4
    fps: float = 60.0
    mean_packets: float = 20.0
    packet_bytes: int = 1200
    deadline_ms: float = 12.0
    jitter_ms: float = 1.0
    high_fraction: float = 0.25
    high_value: float = 4.0
    queue_packets: int = 4096
    background: float = 0.30
    loss: float = 0.10
    size_cv: float = 0.50
    high_size_multiplier: float = 1.0


@dataclass(frozen=True)
class Frame:
    identifier: int
    source: int
    arrival: int
    deadline: int
    packets: int
    value: float
    high: bool


@dataclass(frozen=True)
class Trace:
    frames: tuple[Frame, ...]
    available: np.ndarray
    success: np.ndarray

    def fingerprint(self):
        digest = hashlib.sha256()
        digest.update(json.dumps([asdict(frame) for frame in self.frames], sort_keys=True).encode())
        digest.update(self.available.tobytes())
        digest.update(self.success.tobytes())
        return digest.hexdigest()


@dataclass
class Active:
    frame: Frame
    remaining: int
    attempts: int = 0
    delivered: int = 0


def make_trace(config: Config, seed: int) -> Trace:
    arrival_rng, size_rng, value_rng, background_rng, loss_rng = [
        np.random.default_rng(child) for child in np.random.SeedSequence(seed).spawn(5)
    ]
    duration_slots = round(config.duration_s * 1000 / config.slot_ms)
    deadline_slots = round(config.deadline_ms / config.slot_ms)
    interval_slots = 1000 / config.fps / config.slot_ms
    raw_frames = []
    sigma = math.sqrt(math.log1p(config.size_cv ** 2))
    size_scale = 1 + config.high_fraction * (config.high_size_multiplier - 1)
    for source in range(config.sources):
        phase = arrival_rng.uniform(0, interval_slots)
        for nominal in np.arange(phase, duration_slots, interval_slots):
            jitter = np.clip(arrival_rng.normal(0, config.jitter_ms), -4, 4)
            arrival = max(0, math.ceil(nominal + jitter / config.slot_ms))
            if arrival >= duration_slots:
                continue
            high = bool(value_rng.random() < config.high_fraction)
            size = config.mean_packets * size_rng.lognormal(-sigma * sigma / 2, sigma)
            size *= (config.high_size_multiplier if high else 1) / size_scale
            packets = int(np.clip(round(size), 2, 100))
            raw_frames.append((source, arrival, arrival + deadline_slots, packets,
                               config.high_value if high else 1.0, high))
    raw_frames.sort(key=lambda frame: (frame[1], frame[0]))
    frames = tuple(Frame(identifier, *frame) for identifier, frame in enumerate(raw_frames))
    horizon = max((frame.deadline for frame in frames), default=duration_slots)
    available = background_rng.random(horizon) >= config.background
    success = loss_rng.random(horizon) >= config.loss
    available.flags.writeable = False
    success.flags.writeable = False
    return Trace(frames, available, success)


def simulate(trace: Trace, config: Config, policy: str, alpha: float = 0.0,
             return_outcomes: bool = False):
    if policy not in ('FIFO', 'EDF', 'EDF-safe', 'FA'):
        raise ValueError(policy)
    active = []
    outcomes = []
    next_frame = 0
    queued = 0
    attempts = 0
    delivered = 0
    idle = 0
    statuses = Counter()

    def finish(item, status, completion=None):
        nonlocal queued
        queued -= item.remaining
        statuses[status] += 1
        outcomes.append({**asdict(item.frame), 'status': status,
                         'remaining': item.remaining, 'attempts': item.attempts,
                         'delivered': item.delivered, 'completion': completion})

    for slot in range(len(trace.available)):
        survivors = []
        for item in active:
            if item.frame.deadline <= slot:
                finish(item, 'expired')
            else:
                survivors.append(item)
        active = survivors
        while next_frame < len(trace.frames) and trace.frames[next_frame].arrival == slot:
            frame = trace.frames[next_frame]
            item = Active(frame, frame.packets)
            queued += frame.packets
            if queued > config.queue_packets:
                finish(item, 'overflow')
            else:
                active.append(item)
            next_frame += 1
        if policy in ('EDF-safe', 'FA'):
            survivors = []
            for item in active:
                if item.remaining > item.frame.deadline - slot:
                    finish(item, 'infeasible')
                else:
                    survivors.append(item)
            active = survivors
        if not trace.available[slot]:
            continue
        if not active:
            idle += 1
            continue
        if policy == 'FIFO':
            chosen = min(active, key=lambda item: (item.frame.arrival, item.frame.identifier))
        elif policy in ('EDF', 'EDF-safe'):
            chosen = min(active, key=lambda item: (item.frame.deadline, item.frame.identifier))
        else:
            chosen = max(active, key=lambda item: (
                item.frame.value ** alpha / (item.remaining * (item.frame.deadline - slot)),
                -item.frame.deadline, -item.frame.identifier))
        attempts += 1
        chosen.attempts += 1
        if trace.success[slot]:
            chosen.remaining -= 1
            chosen.delivered += 1
            queued -= 1
            delivered += 1
            if chosen.remaining == 0:
                finish(chosen, 'complete', slot + 1)
                active.remove(chosen)
        if not (0 <= queued <= config.queue_packets):
            raise AssertionError('Integrity check failed: 0 <= queued <= config.queue_packets')
    for item in active:
        if not (item.frame.deadline <= len(trace.available)):
            raise AssertionError('Integrity check failed: item.frame.deadline <= len(trace.available)')
        finish(item, 'expired')
    if not (next_frame == len(trace.frames)):
        raise AssertionError('Integrity check failed: next_frame == len(trace.frames)')
    if not (queued == 0):
        raise AssertionError('Integrity check failed: queued == 0')
    complete = [item for item in outcomes if item['status'] == 'complete']
    failed = [item for item in outcomes if item['status'] != 'complete']
    high_frames = [item for item in outcomes if item['high']]
    low_frames = [item for item in outcomes if not item['high']]
    total_packets = sum(item['packets'] for item in outcomes)
    complete_packets = sum(item['packets'] for item in complete)
    wasted_attempts = sum(item['attempts'] for item in failed)
    completed_retries = sum(item['attempts'] - item['packets'] for item in complete)
    available_count = int(trace.available.sum())
    if not (len(outcomes) == len(trace.frames)):
        raise AssertionError('Integrity check failed: len(outcomes) == len(trace.frames)')
    if not (total_packets == delivered + sum(item['remaining'] for item in outcomes)):
        raise AssertionError("Integrity check failed: total_packets == delivered + sum(item['remaining'] for item in outcomes)")
    if not (attempts == sum(item['attempts'] for item in outcomes)):
        raise AssertionError("Integrity check failed: attempts == sum(item['attempts'] for item in outcomes)")
    if not (attempts == complete_packets + completed_retries + wasted_attempts):
        raise AssertionError('Integrity check failed: attempts == complete_packets + completed_retries + wasted_attempts')
    if not (attempts + idle == available_count):
        raise AssertionError('Integrity check failed: attempts + idle == available_count')
    if not (all(item['completion'] <= item['deadline'] for item in complete)):
        raise AssertionError("Integrity check failed: all(item['completion'] <= item['deadline'] for item in complete)")
    metrics = {
        'complete_fraction': len(complete) / len(outcomes) if outcomes else 0.0,
        'weighted_fraction': sum(item['value'] for item in complete) /
            sum(item['value'] for item in outcomes) if outcomes else 0.0,
        'high_fraction': sum(item['status'] == 'complete' for item in high_frames) /
            len(high_frames) if high_frames else 0.0,
        'low_fraction': sum(item['status'] == 'complete' for item in low_frames) /
            len(low_frames) if low_frames else 0.0,
        'wasted_bytes': wasted_attempts * config.packet_bytes,
        'wasted_received_bytes': sum(item['delivered'] for item in failed) * config.packet_bytes,
        'completed_retry_bytes': completed_retries * config.packet_bytes,
        'useful_payload_bytes': complete_packets * config.packet_bytes,
        'attempted_bytes': attempts * config.packet_bytes,
        'waste_share': wasted_attempts / attempts if attempts else 0.0,
        'packet_delivery_fraction': delivered / total_packets if total_packets else 0.0,
        'generated_frames': len(outcomes), 'high_frames': len(high_frames),
        'generated_packets': total_packets, 'mean_frame_packets': total_packets / len(outcomes)
            if outcomes else 0.0,
        'frame_size_cv_actual': float(np.std([item['packets'] for item in outcomes]) /
            np.mean([item['packets'] for item in outcomes])) if outcomes else 0.0,
        'offered_mbps': total_packets * config.packet_bytes * 8 / config.duration_s / 1e6,
        'attempts': attempts, 'delivered_packets': delivered,
        'available_slots': available_count, 'background_slots': len(trace.available) - available_count,
        'idle_slots': idle, 'horizon_slots': len(trace.available),
        'infeasible_frames': statuses['infeasible'], 'expired_frames': statuses['expired'],
        'overflow_frames': statuses['overflow'], 'completed_frames': len(complete),
    }
    return (metrics, outcomes) if return_outcomes else metrics


def planned_scenarios():
    for background in (0.0, 0.15, 0.30, 0.45, 0.60):
        for size_cv in (0.10, 0.50):
            for loss in (0.0, 0.10):
                yield 'main', Config(background=background, size_cv=size_cv, loss=loss), [
                    ('FIFO', 0.0), ('EDF', 0.0), ('EDF-safe', 0.0),
                    *[('FA', alpha) for alpha in (0.0, 0.25, 0.5, 1.0, 2.0)]]
    for background in (0.30, 0.45, 0.60):
        yield 'large_important', Config(background=background, high_size_multiplier=3.0), [
            ('FA', alpha) for alpha in (0.0, 1.0, 2.0)]
    yield 'longer_run', Config(background=0.45, duration_s=12.0), [('FA', 0.0), ('FA', 1.0)]

