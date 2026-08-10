"""
project_paths.py: single source of truth for every path in the project.

Nothing in this repository contains an absolute path. Every location is derived
from this file's own location, so the project runs unchanged after a fresh clone
on any machine or OS.

Assumed layout (this file lives in <data_root>/scripts/):

    <repo_root>/
        project/          <- DATA_DIR
            input/                   <- INPUT_DIR: everything the pipeline reads
                subjects_information_audio_lanzhou_2015.xlsx
                audio_lanzhou_2015_og/       <- RAW_AUDIO_DIR: 02010001/ 02010002/ ...
                audio_lanzhou_2015_resampled/
                audio_lanzhou_2015_noisy/  audio_snr*/  audio_random/
            output/                  <- OUTPUT_DIR: everything generated
                csv/                 <- CSV_DIR
                plots/               <- PLOTS_DIR
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
    "SCRIPTS_DIR", "DATA_DIR", "REPO_ROOT", "INPUT_DIR", "RAW_AUDIO_DIR",
    "OUTPUT_DIR", "CSV_DIR", "PLOTS_DIR",
    "SUBJECTS_XLSX", "WAV_INVENTORY", "WAV_INVENTORY_CLEANED",
    "RESAMPLED_DIR", "NOISY_DIR",
    "EGEMAPS_CSV", "EGEMAPS_NOISY_CSV", "MODEL_DF_CSV",
    "OPENSMILE_DIR", "SMILEXTRACT", "EGEMAPS_CONF",
    "require",
]

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent           # .../project/scripts
DATA_DIR = SCRIPTS_DIR.parent                           # .../project
REPO_ROOT = DATA_DIR.parent

_env_data = os.environ.get("MODMA_DATA_DIR")
if _env_data:
    DATA_DIR = Path(_env_data).expanduser().resolve()

# Source data lives under <data_root>/input/ and everything the notebooks
# generate under <data_root>/output/, so inputs and artefacts never mix and the
# generated side can be cleaned as a unit.
INPUT_DIR = DATA_DIR / "input"
RAW_AUDIO_DIR = INPUT_DIR / "audio_lanzhou_2015_og"   # 0*/ subject folders, as delivered

OUTPUT_DIR = DATA_DIR / "output"
CSV_DIR    = OUTPUT_DIR / "csv"      # every generated .csv (data tables + results)
PLOTS_DIR  = OUTPUT_DIR / "plots"    # every generated figure
for _d in (CSV_DIR, PLOTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data files (inputs and derived artefacts, all directly under DATA_DIR)
# ---------------------------------------------------------------------------
SUBJECTS_XLSX = INPUT_DIR / "subjects_information_audio_lanzhou_2015.xlsx"

WAV_INVENTORY = CSV_DIR / "wav_inventory.csv"
WAV_INVENTORY_CLEANED = CSV_DIR / "wav_inventory_cleaned.csv"

RESAMPLED_DIR = INPUT_DIR / "audio_lanzhou_2015_resampled"   # 16 kHz mono WAVs
NOISY_DIR = INPUT_DIR / "audio_lanzhou_2015_noisy"           # + white noise @ SNR

EGEMAPS_CSV = CSV_DIR / "egemaps_features.csv"             # per-recording features
EGEMAPS_NOISY_CSV = CSV_DIR / "egemaps_features_noisy.csv"
MODEL_DF_CSV = CSV_DIR / "model_df.csv"                    # per-subject modeling table

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
    print(f"INPUT_DIR   = {INPUT_DIR}")
    print(f"CSV_DIR     = {CSV_DIR}")
    print(f"PLOTS_DIR   = {PLOTS_DIR}")
    print()
    for name in ("SUBJECTS_XLSX", "WAV_INVENTORY", "EGEMAPS_CSV", "MODEL_DF_CSV",
                 "RESAMPLED_DIR", "NOISY_DIR", "SMILEXTRACT", "EGEMAPS_CONF"):
        p = globals()[name]
        print(f"  [{'x' if p.exists() else ' '}] {name:22s} {p}")
