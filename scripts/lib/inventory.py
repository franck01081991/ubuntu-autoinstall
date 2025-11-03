from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OVERLAY = REPO_ROOT / "baremetal" / "inventory-local"
REPO_INVENTORY_ROOT = REPO_ROOT / "baremetal" / "inventory"


@lru_cache(maxsize=None)
def get_overlay_root() -> Path:
    """Return the inventory overlay directory (outside Git history)."""

    raw = os.environ.get("AUTOINSTALL_LOCAL_DIR")
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_OVERLAY


def iter_inventory_roots(include_overlay: bool = True) -> List[Path]:
    """Return inventory roots, overlay first when requested."""

    roots: list[Path] = []
    if include_overlay:
        overlay = get_overlay_root()
        roots.append(overlay)
    roots.append(REPO_INVENTORY_ROOT)
    return roots


def host_vars_candidates(host: str, include_overlay: bool = True) -> List[Path]:
    """Candidate directories that may contain host-specific vars."""

    host_dirs: list[Path] = []
    for root in iter_inventory_roots(include_overlay=include_overlay):
        candidate = root / "host_vars" / host
        host_dirs.append(candidate)
    return host_dirs


def hardware_profiles_roots(include_overlay: bool = True) -> List[Path]:
    """Candidate directories containing hardware profiles."""

    return [root / "profiles" / "hardware" for root in iter_inventory_roots(include_overlay=include_overlay)]


def first_existing(paths: Iterable[Path]) -> Path | None:
    """Return the first existing path from an iterable."""

    for path in paths:
        if path.exists():
            return path
    return None
