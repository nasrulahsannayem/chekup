"""Display helper utilities for Chekup TUI."""

from __future__ import annotations


def human(size_bytes: int | float) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes is None:
        return "0 B"
    val = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(val) < 1024:
            return f"{val:.1f} {unit}"
        val /= 1024
    return f"{val:.1f} PB"


def age(seconds: float) -> str:
    """Format seconds into *Xd Yh Zm*."""
    seconds = max(0, int(seconds))
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    return f"{d}d {h}h {m}m"


__all__ = ["human", "age"]
