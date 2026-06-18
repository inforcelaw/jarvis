from __future__ import annotations

from dataclasses import dataclass
import time

from jarvis_core.config import ClapSettings


@dataclass(frozen=True)
class ClapEvent:
    gap_s: float
    level: float
    noise_floor: float
    threshold: float
    timestamp_monotonic: float


class DoubleClapDetector:
    """Stateful double-clap detector based on the original Jarvis script.

    Feed it RMS levels from microphone blocks. It returns a ClapEvent only when
    two qualifying spikes occur inside the configured timing window.
    """

    def __init__(self, settings: ClapSettings):
        self.settings = settings
        self.noise_floor = 1e-4
        self.last_double = 0.0
        self.first_clap_time: float | None = None
        self.spike_armed = True

    def update(self, level: float, now: float | None = None) -> ClapEvent | None:
        now = time.monotonic() if now is None else now
        s = self.settings

        quiet_gate = self.noise_floor * s.quiet_gate_mult
        if level < quiet_gate:
            self.noise_floor = s.noise_floor_alpha * self.noise_floor + (
                1.0 - s.noise_floor_alpha
            ) * level
            self.noise_floor = max(self.noise_floor, 1e-7)

        threshold = max(self.noise_floor * s.spike_ratio, s.min_rms)
        retrigger_level = threshold * s.retrigger_ratio

        if level < retrigger_level:
            self.spike_armed = True

        if not self.spike_armed:
            return None
        if level < threshold:
            return None
        if (now - self.last_double) < s.cooldown_s:
            return None

        self.spike_armed = False

        if self.first_clap_time is None:
            self.first_clap_time = now
            return None

        gap = now - self.first_clap_time
        if gap < s.min_double_gap_s:
            return None
        if gap <= s.max_double_gap_s:
            self.first_clap_time = None
            self.last_double = now
            return ClapEvent(
                gap_s=gap,
                level=level,
                noise_floor=self.noise_floor,
                threshold=threshold,
                timestamp_monotonic=now,
            )

        self.first_clap_time = now
        return None
