"""Platform-independent hourly boundary detection and original watch-like tone."""
from collections import deque
from datetime import timedelta
import math
import struct
import wave


class HourlyChime:
    def __init__(self):
        self.previous = None
        self.rung = deque(maxlen=48)

    def reset(self):
        """Re-arm after enabling/disabling; retain duplicate protection."""
        self.previous = None

    def poll(self, now, elapsed, enabled=True):
        previous = self.previous
        self.previous = (now, elapsed, enabled)
        if not enabled or previous is None or not previous[2]:
            return False
        before, before_elapsed, _ = previous
        wall_delta = now.timestamp() - before.timestamp()
        monotonic_delta = elapsed - before_elapsed
        # A late wake or wall-clock jump must not replay a missed signal.
        if not (0 < wall_delta <= 3 and 0 < monotonic_delta <= 3
                and abs(wall_delta - monotonic_delta) <= 0.5):
            return False
        boundary = now.replace(minute=0, second=0, microsecond=0)
        if not (now - boundary < timedelta(seconds=2)
                and before.timestamp() < boundary.timestamp()):
            return False
        key = boundary.timestamp()
        if key in self.rung:
            return False
        self.rung.append(key)
        return True


def write_chime(path):
    """Two complete 120ms tones, gentle release and quiet playback tail, PCM16 mono."""
    rate, length, gap = 44100, 0.120, 0.070
    count = round(rate * length)
    tone = []
    for index in range(count):
        attack = min(1.0, index / (rate * 0.003))
        release = min(1.0, (count - 1 - index) / (rate * 0.012))
        edge = attack * (0.5 - 0.5 * math.cos(math.pi * release))
        tone.append(round(32767 * 0.45 * edge * math.sin(2 * math.pi * 4096 * index / rate)))
    samples = tone + [0] * round(rate * gap) + tone + [0] * round(rate * 0.050)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
