"""Process RSS memory logging for Render's 512MB instance.

Every pipeline stage logs ``[MEM] <stage> <rss>MB`` so OOM regressions are
visible in structured logs before the kernel OOM-killer is.
"""

import logging
import os

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a runtime requirement
    psutil = None

logger = logging.getLogger("orbit.memory")

_process = None


def rss_mb() -> int:
    """Current process resident set size in whole megabytes."""
    global _process
    if psutil is None:  # pragma: no cover - defensive fallback
        return 0
    if _process is None:
        _process = psutil.Process(os.getpid())
    try:
        return int(_process.memory_info().rss / (1024 * 1024))
    except Exception:  # pragma: no cover - process may be shutting down
        return 0


def log_rss(stage: str) -> int:
    """Log ``[MEM] <stage> <rss>MB`` and return the RSS in MB."""
    megabytes = rss_mb()
    logger.info("[MEM] %s %dMB", stage, megabytes)
    return megabytes
