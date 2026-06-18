from __future__ import annotations

import numpy as np


def rms_mono(block: np.ndarray) -> float:
    """Return RMS volume for a mono/stereo float audio block."""
    if block.ndim > 1:
        data = np.mean(block.astype(np.float64), axis=1)
    else:
        data = block.astype(np.float64)
    if data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(data**2)))
