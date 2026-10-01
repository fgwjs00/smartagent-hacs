# Generated from contracts/python/host_resources.py; do not edit.
"""Host-local procfs sampling with explicit I/O, clock and diagnostic dependencies."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TextIO

CpuSnapshot = tuple[int, int]


def clamp_percent(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric != numeric or numeric < 0:
        return 0.0
    if numeric > 100:
        return 100.0
    return round(numeric, 1)


def cpu_percent_between(before: CpuSnapshot, after: CpuSnapshot) -> float | None:
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0 or idle_delta < 0:
        return None
    return clamp_percent(max(0, total_delta - idle_delta) * 100.0 / total_delta)


class ProcResourceReader:
    """Each process owns its own sample; no state crosses HA/add-on boundaries."""

    def __init__(
        self, *, open_text: Callable[..., TextIO],
        sleep: Callable[[float], None], report: Callable[[str, str], None],
    ) -> None:
        self._open_text = open_text
        self._sleep = sleep
        self._report = report
        self.cpu_snapshot: CpuSnapshot | None = None

    def read_cpu_snapshot(self) -> CpuSnapshot | None:
        try:
            with self._open_text("/proc/stat", "r", encoding="utf-8") as stream:
                line = stream.readline()
        except OSError as exc:
            self._report("ProcResourceReader.read_cpu_snapshot:read", type(exc).__name__)
            return None
        parts = line.split()
        if not parts or parts[0] != "cpu":
            self._report("ProcResourceReader.read_cpu_snapshot:parse", "missing_cpu_row")
            return None
        try:
            values = [int(item) for item in parts[1:]]
        except ValueError:
            self._report("ProcResourceReader.read_cpu_snapshot:parse", "invalid_counter")
            return None
        if len(values) < 4:
            self._report("ProcResourceReader.read_cpu_snapshot:parse", "insufficient_counters")
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle

    def read_cpu_percent(self) -> float | None:
        current = self.read_cpu_snapshot()
        if current is None:
            return None
        previous = self.cpu_snapshot
        if previous is None:
            self._sleep(0.05)
            sampled = self.read_cpu_snapshot()
            self.cpu_snapshot = sampled or current
            if sampled is None:
                return None
            previous, current = current, sampled
        else:
            self.cpu_snapshot = current
        value = cpu_percent_between(previous, current)
        if value is None:
            self._report("ProcResourceReader.read_cpu_percent:delta", "invalid_sample_delta")
        return value

    def _memory_fields(self) -> dict[str, float] | None:
        fields: dict[str, float] = {}
        try:
            with self._open_text("/proc/meminfo", "r", encoding="utf-8") as stream:
                for line in stream:
                    if ":" not in line:
                        continue
                    key, raw = line.split(":", 1)
                    parts = raw.strip().split()
                    if not parts:
                        continue
                    try:
                        fields[key] = float(parts[0])
                    except ValueError:
                        self._report("ProcResourceReader._memory_fields:parse", "invalid_counter")
        except OSError as exc:
            self._report("ProcResourceReader._memory_fields:read", type(exc).__name__)
            return None
        return fields

    def read_memory_percent(self) -> float | None:
        fields = self._memory_fields()
        if fields is None:
            return None
        total = fields.get("MemTotal", 0.0)
        available = fields.get("MemAvailable")
        if available is None:
            available = fields.get("MemFree", 0.0) + fields.get("Buffers", 0.0) + fields.get("Cached", 0.0)
        if total <= 0 or available is None:
            self._report("ProcResourceReader.read_memory_percent:parse", "missing_memory_total")
            return None
        return clamp_percent(((total - available) * 100.0) / total)
