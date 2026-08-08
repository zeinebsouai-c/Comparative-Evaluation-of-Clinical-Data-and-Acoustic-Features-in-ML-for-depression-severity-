"""
project_config.py: single source of truth for the whole thesis project.

Paths live in project_paths.py and are re-exported here, so importing this
module is all an analysis notebook needs. Import at the top of EVERY analysis
notebook (training, cv, robustness, interpretability, error analysis), after the
portable bootstrap cell that puts scripts/ on sys.path:

    import sys
    from pathlib import Path

    def _find_scripts_dir():
        start = Path.cwd().resolve()
        for base in (start, *start.parents):
            for cand in (base / "scripts", base,
                         *sorted(base.glob("*/scripts")), *sorted(base.glob("*/*/scripts"))):
                if (cand / "project_paths.py").is_file():
                    return cand
        raise FileNotFoundError("scripts/project_paths.py not found ...")

    sys.path.insert(0, str(_find_scripts_dir()))
    from project_config import *

    model_df = load_model_df()
    y = model_df["phq9"]

Then use the CONSTANTS below everywhere. Never redefine `acoustic` or the clinical
feature lists inline, and never write an absolute path into a notebook.
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd

from project_paths import *          # DATA_DIR, FIG_DIR, MODEL_DF_CSV, ... (see project_paths.py)
from project_paths import require

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
REPEATED_CV_SEEDS = range(20)

# ---------------------------------------------------------------------------
# Data location comes from project_paths (derived from this file's location, so
# it is independent of the notebook's working directory). Re-exported above.
# ---------------------------------------------------------------------------
# Clinical / demographic feature sets (UPPERCASE = canonical constants)
#
# PSYCH_ALL  = every questionnaire column present in model_df.
# PSYCH      = the subset actually modelled.
#
# PSQI is excluded from the modelling set: its sleep items overlap PHQ-9 item 3
# IMPORTANT: a scale dropped from PSYCH must stay in PSYCH_ALL because ACOUSTIC is
# carved out of model_df by subtraction below, so anything missing from
# _NON_ACOUSTIC would silently become an "acoustic" feature.
# ---------------------------------------------------------------------------
DEMO      = ["age", "gender", "education_years"]
PSYCH_ALL = ["ctq_sf", "LES", "SSRS", "gad7", "PSQI"]
EXCLUDED_SCALES = ["PSQI"]

PSYCH    = [c for c in PSYCH_ALL if c not in EXCLUDED_SCALES]    # 4
CLINICAL = DEMO + PSYCH                                          # 7

_ID_TARGET    = ["subject_key", "phq9"]
_NON_ACOUSTIC = _ID_TARGET + DEMO + PSYCH_ALL

# ---------------------------------------------------------------------------
# A-priori functional-collapse rule: keep mean + coefficient of variation per
# LLD, drop the redundant/noise-prone percentile, percentile-range, and
# rising/falling-slope functionals. (Note: 'RisingSlope'/'FallingSlope', NOT
# bare 'slope', so the spectral slopeV LLDs are preserved.)
# ---------------------------------------------------------------------------
_DROP_MARKERS = ["percentile", "pctlrange", "RisingSlope", "FallingSlope"]

def collapse_functionals(names):
    return [c for c in names if not any(m in c for m in _DROP_MARKERS)]

# ---------------------------------------------------------------------------
# Canonical acoustic feature sets, derived once from model_df's columns
# ---------------------------------------------------------------------------
def load_model_df() -> pd.DataFrame:
    require(MODEL_DF_CSV, "Build it by running MODMA_audio_processing.ipynb end to end.")
    return pd.read_csv(MODEL_DF_CSV, dtype={"subject_key": str})

_MDF = load_model_df()
ACOUSTIC_FULL = [c for c in _MDF.columns if c not in _NON_ACOUSTIC]   # 88
ACOUSTIC      = collapse_functionals(ACOUSTIC_FULL)                   # 72  <-- USE THIS

# Convenience combined sets
DEMO_ACOUSTIC     = DEMO + ACOUSTIC
CLINICAL_ACOUSTIC = CLINICAL + ACOUSTIC

CANONICAL_ORDER = _MDF["subject_key"].astype(int).tolist()

# ---------------------------------------------------------------------------
# Per-recording -> subject-level aggregation (drop-recordings / noise experiments)
# ---------------------------------------------------------------------------
def subject_means(df, feats=None):
    """Aggregate an ALREADY-LOADED per-recording df to subject means, aligned to
    CANONICAL_ORDER so fold assignments match the model_df-based tables."""
    if feats is None:
        feats = ACOUSTIC
    X = df.groupby("subject_id")[feats].mean()
    X.index = X.index.astype(int)
    X = X.loc[[i for i in CANONICAL_ORDER if i in X.index]]   # canonical order
    y = df.groupby("subject_id")["phq9"].first()
    y.index = y.index.astype(int)
    y = y.loc[X.index]
    return X, y

def subject_table(csv, feats=None):
    """Load a per-recording CSV and aggregate to aligned subject means.

    `csv` may be a bare file name (resolved against DATA_DIR) or a full Path.
    """
    if feats is None:
        feats = ACOUSTIC
    path = Path(csv)
    if not path.is_absolute():
        path = DATA_DIR / path
    f = pd.read_csv(require(path), dtype={"subject_id": str}).dropna(subset=["phq9"])
    missing = [c for c in feats if c not in f.columns]
    if missing:
        raise ValueError(f"{csv} missing {len(missing)} features, e.g. {missing[:3]}")
    return subject_means(f, feats)

# ---------------------------------------------------------------------------
# Acoustic feature -> interpretable category (GeMAPS; Eyben et al. 2016).
# Perturbation measures jitter + shimmer grouped with HNR under Voice quality.
# Uses PSYCH_ALL so an excluded scale is still labelled correctly if it turns up
# in a table (e.g. the PSQI-only baseline).
# ---------------------------------------------------------------------------
def categorize(feat):
    if feat in DEMO:      return "Demographics"
    if feat in PSYCH_ALL: return "Clinical"
    fl = feat.lower()
    if any(k in fl for k in ["segmentlength", "segmentspersec", "peakspersec"]): return "Timing/Pauses"
    if "f0semitone" in fl:                                                        return "Pitch"
    if "loudness" in fl or "equivalentsoundlevel" in fl:                          return "Loudness/Energy"
    if any(k in fl for k in ["jitter", "shimmer", "hnr", "h1-h2", "h1-a3"]):      return "Voice quality"
    if re.match(r"f[123](frequency|bandwidth|amplitude)", fl):                    return "Formants"
    if any(k in fl for k in ["alpharatio", "hammarberg", "slope", "spectralflux", "mfcc"]): return "Spectral"
    return "Other"

# ---------------------------------------------------------------------------
# Canonical repeated-CV scorer --> returns {metric: (mean, std)} across seeds.
# Use this everywhere instead of per-notebook `evaluate` copies.
# ---------------------------------------------------------------------------
def repeated_cv(estimator, X, y, seeds=REPEATED_CV_SEEDS, n_splits=10):
    from sklearn.model_selection import KFold, cross_val_predict
    from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
    from scipy.stats import pearsonr
    rows = []
    for s in seeds:
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=s)
        p = cross_val_predict(estimator, X, y, cv=kf, n_jobs=-1)
        rows.append({"MAE": mean_absolute_error(y, p),
                     "RMSE": np.sqrt(mean_squared_error(y, p)),
                     "R2": r2_score(y, p),
                     "r": pearsonr(y, p)[0]})
    d = pd.DataFrame(rows)
    return {k: (d[k].mean(), d[k].std()) for k in ["MAE", "RMSE", "R2", "r"]}


if __name__ == "__main__":
    print(f"DATA_DIR = {DATA_DIR}")
    print(f"excluded scales: {EXCLUDED_SCALES or 'none'}")
    print(f"DEMO={len(DEMO)} PSYCH={len(PSYCH)} CLINICAL={len(CLINICAL)} "
          f"ACOUSTIC_FULL={len(ACOUSTIC_FULL)} ACOUSTIC={len(ACOUSTIC)}")
    for s in EXCLUDED_SCALES:
        assert s not in CLINICAL,      f"{s} leaked back into the modelling set"
        assert s not in ACOUSTIC_FULL, f"{s} leaked into the acoustic set"
    assert len(ACOUSTIC) == 72, f"Expected 72 collapsed features, got {len(ACOUSTIC)}"
    print("OK — feature sets are consistent.")
