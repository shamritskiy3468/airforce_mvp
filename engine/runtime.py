from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .engine import SimulationEngine


@dataclass(frozen=True)
class RunStats:
    steps: int
    events: int
    elapsed_real_seconds: float
    avg_step_lag_seconds: float = 0.0
    max_step_lag_seconds: float = 0.0

    @property
    def events_per_second(self) -> float:
        if self.elapsed_real_seconds <= 0:
            return 0.0
        return self.events / self.elapsed_real_seconds


def run_fast(engine: SimulationEngine, steps: int) -> RunStats:
    """
    Просто прогоняет steps тиков максимально быстро (без pacing).
    """
    t0 = time.perf_counter()
    events = 0
    for _ in range(steps):
        events += engine.step()
    t1 = time.perf_counter()
    return RunStats(
        steps=steps,
        events=events,
        elapsed_real_seconds=(t1 - t0),
        avg_step_lag_seconds=0.0,
        max_step_lag_seconds=0.0,
    )


def run_realtime(
    engine: SimulationEngine,
    steps: int,
    time_scale: float = 1.0,
    sleep_max_seconds: float = 0.05,
) -> RunStats:
    """
    "Правильный" realtime loop (или ускоренный), без привязки к print/sink.

    time_scale:
      - 1.0  → 1 сек реального времени = 1 сек сим-времени
      - 10.0 → 1 реальная сек = 10 сим-сек (ускорение)

    Пейсинг:
      target_real_step = tick_seconds / time_scale
    """
    if time_scale <= 0:
        raise ValueError("time_scale must be > 0")

    tick_seconds = engine.config.time.tick_seconds
    target_step_real = tick_seconds / time_scale

    t0 = time.perf_counter()
    next_deadline = t0
    events = 0
    lag_sum = 0.0
    lag_max = 0.0

    for _ in range(steps):
        # Делаем шаг
        events += engine.step()

        # Ждём до дедлайна следующего шага
        next_deadline += target_step_real
        now = time.perf_counter()
        sleep_for = next_deadline - now
        step_lag = max(0.0, -sleep_for)
        lag_sum += step_lag
        if step_lag > lag_max:
            lag_max = step_lag
        if sleep_for > 0:
            time.sleep(min(sleep_for, sleep_max_seconds))

    t1 = time.perf_counter()
    return RunStats(
        steps=steps,
        events=events,
        elapsed_real_seconds=(t1 - t0),
        avg_step_lag_seconds=(lag_sum / steps if steps > 0 else 0.0),
        max_step_lag_seconds=lag_max,
    )

