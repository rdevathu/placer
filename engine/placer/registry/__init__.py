"""Pathway registry: the catalog of 25 discharge pathways Placer knows about.

Only the ``wired`` pathways have full requirement checklists and downstream
automation in this wave; the rest exist so predictions can name them and the
team can see them on the board. Loaded once from YAML and cached — the catalog
is static per process (edit the YAML and restart to change it).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_PATHWAYS_FILE = Path(__file__).resolve().parent / "pathways.yaml"


@lru_cache(maxsize=1)
def load_pathways() -> dict:
    """Return the pathway catalog keyed by integer pathway id."""
    with open(_PATHWAYS_FILE) as f:
        raw = yaml.safe_load(f)
    return {p["id"]: p for p in raw["pathways"]}
