"""
project_paths.py: single source of truth for every path in the project.

Nothing in this repository contains an absolute path. Every location is derived
from this file's own location, so the project runs unchanged after a fresh clone
on any machine or OS.

Assumed layout (this file lives in <data_root>/scripts/):

    <repo_root>/
        audio_lanzhou_2015/          <- DATA_DIR: all data + result files
            subjects_information_audio_lanzhou_2015.xlsx
            02010001/ 02010002/ ...  <- raw subject folders (not in git)
            tools/opensmile-3.0-win-x64/
            scripts/                 <- SCRIPTS_DIR: this file + the notebooks

Notebooks have no __file__, so they locate this module with the bootstrap cell
at the top of each notebook, then do `from project_paths import *` (or
`from project_config import *`, which re-exports everything below).

Environment overrides (optional; useful when the raw audio is kept outside the
repo, e.g. on an external drive):

    MODMA_DATA_DIR   -> use this directory as DATA_DIR instead of scripts/..
    OPENSMILE_ROOT   -> root of an openSMILE install outside tools/
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "SCRIPTS_DIR", "DATA_DIR", "REPO_ROOT", "FIG_DIR", "PLOTS_DIR",
    "SUBJECTS_XLSX", "WAV_INVENTORY", "WAV_INVENTORY_CLEANED",
    "RESAMPLED_DIR", "NOISY_DIR",
    "EGEMAPS_CSV", "EGEMAPS_NOISY_CSV", "MODEL_DF_CSV",
    "OPENSMILE_DIR", "SMILEXTRACT", "EGEMAPS_CONF",
    "require",
]

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent           # .../audio_lanzhou_2015/scripts
DATA_DIR = SCRIPTS_DIR.parent                           # .../audio_lanzhou_2015
REPO_ROOT = DATA_DIR.parent

_env_data = os.environ.get("MODMA_DATA_DIR")
if _env_data:
    DATA_DIR = Path(_env_data).expanduser().resolve()

# Figures are written next to the notebooks that produce them.
FIG_DIR = SCRIPTS_DIR

# Exported figures for the write-up: <data_root>/plots/, a sibling of scripts/.
PLOTS_DIR = DATA_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data files (inputs and derived artefacts, all directly under DATA_DIR)
# ---------------------------------------------------------------------------
SUBJECTS_XLSX = DATA_DIR / "subjects_information_audio_lanzhou_2015.xlsx"

WAV_INVENTORY = DATA_DIR / "wav_inventory.csv"
WAV_INVENTORY_CLEANED = DATA_DIR / "wav_inventory_cleaned.csv"

RESAMPLED_DIR = DATA_DIR / "audio_lanzhou_2015_resampled"   # 16 kHz mono WAVs
NOISY_DIR = DATA_DIR / "audio_lanzhou_2015_noisy"           # + white noise @ SNR

EGEMAPS_CSV = DATA_DIR / "egemaps_features.csv"             # per-recording features
EGEMAPS_NOISY_CSV = DATA_DIR / "egemaps_features_noisy.csv"
MODEL_DF_CSV = DATA_DIR / "model_df.csv"                    # per-subject modeling table

# ---------------------------------------------------------------------------
# openSMILE (eGeMAPS extraction). Bundled under tools/ by default.
# ---------------------------------------------------------------------------
_env_smile = os.environ.get("OPENSMILE_ROOT")
OPENSMILE_DIR = (Path(_env_smile).expanduser().resolve() if _env_smile
                 else DATA_DIR / "tools" / "opensmile-3.0-win-x64")

_exe = "SMILExtract.exe" if os.name == "nt" else "SMILExtract"
SMILEXTRACT = OPENSMILE_DIR / "bin" / _exe
EGEMAPS_CONF = OPENSMILE_DIR / "config" / "egemaps" / "v01a" / "eGeMAPSv01a.conf"


# ---------------------------------------------------------------------------
# Helper: fail early with an actionable message instead of a bare FileNotFound
# ---------------------------------------------------------------------------
def require(path: Path, hint: str = "") -> Path:
    """Return `path`, or raise with a message explaining which step produces it."""
    path = Path(path)
    if not path.exists():
        msg = f"Missing: {path}"
        if hint:
            msg += f"\n  -> {hint}"
        msg += f"\n  (DATA_DIR = {DATA_DIR}; override with the MODMA_DATA_DIR env var)"
        raise FileNotFoundError(msg)
    return path


if __name__ == "__main__":
    print(f"REPO_ROOT   = {REPO_ROOT}")
    print(f"DATA_DIR    = {DATA_DIR}")
    print(f"SCRIPTS_DIR = {SCRIPTS_DIR}")
    print()
    for name in ("SUBJECTS_XLSX", "WAV_INVENTORY", "EGEMAPS_CSV", "MODEL_DF_CSV",
                 "RESAMPLED_DIR", "NOISY_DIR", "SMILEXTRACT", "EGEMAPS_CONF"):
        p = globals()[name]
        print(f"  [{'x' if p.exists() else ' '}] {name:22s} {p}")
